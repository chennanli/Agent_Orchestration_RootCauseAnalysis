import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Group,
  PasswordInput,
  Select,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconBolt, IconKey, IconCheck } from "@tabler/icons-react";
import { ModelInfo, listModels } from "../api/agent";

interface Props {
  selectedModelId: string | null;
  onChange: (modelId: string, apiKey: string | null) => void;
}

const STORAGE_PREFIX = "tep_copilot_api_key__";

/**
 * Model dropdown + bring-your-own-key input.
 *
 * Behaviour:
 *   - Fetches `/api/agent/models` on mount.
 *   - Each model declares which env var holds its API key. If the server
 *     reports `api_key_present: true`, no input is needed.
 *   - If the key is NOT in the env, the UI shows a masked password input
 *     so the user can paste their own key. The key is persisted in
 *     `localStorage` under `tep_copilot_api_key__<env_var>` (so it survives
 *     reloads on this machine but never leaves it).
 *   - Calls `onChange(model_id, api_key_or_null)` whenever either changes.
 */
export default function ModelSelector({ selectedModelId, onChange }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultId, setDefaultId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string>("");

  // Fetch the manifest once.
  useEffect(() => {
    let cancelled = false;
    listModels()
      .then((r) => {
        if (cancelled) return;
        setModels(r.models);
        setDefaultId(r.default);
        if (!selectedModelId) onChange(r.default, _loadKeyFor(r.models, r.default));
      })
      .catch((e) => !cancelled && setError((e as Error).message));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = models.find((m) => m.id === (selectedModelId || defaultId));
  const needsByokKey = current && !current.api_key_present;

  // Re-load any previously saved key for this model when selection changes.
  useEffect(() => {
    if (!current) return;
    setApiKey(_loadKeyFor(models, current.id) ?? "");
  }, [current?.id, models]);

  const saveAndUseKey = () => {
    if (!current) return;
    const key = apiKey.trim();
    if (key) {
      localStorage.setItem(STORAGE_PREFIX + current.api_key_env, key);
      onChange(current.id, key);
    } else {
      localStorage.removeItem(STORAGE_PREFIX + current.api_key_env);
      onChange(current.id, null);
    }
  };

  return (
    <Stack gap={6}>
      <Group gap={6} align="center">
        <IconBolt size={14} />
        <Text size="xs" c="dimmed" fw={600}>
          Model
        </Text>
      </Group>

      <Select
        data={models.map((m) => ({
          value: m.id,
          label: m.api_key_present
            ? m.label
            : `${m.label}  (needs ${m.api_key_env})`,
        }))}
        value={selectedModelId || defaultId || null}
        onChange={(v) => {
          if (!v) return;
          onChange(v, _loadKeyFor(models, v));
        }}
        size="xs"
        comboboxProps={{ withinPortal: true }}
        allowDeselect={false}
        placeholder="select model"
        error={error || undefined}
      />

      {current && needsByokKey && (
        <Stack gap={4} mt={4}>
          <Group gap={4} align="center">
            <IconKey size={12} />
            <Text size="xs" c="dimmed">
              Bring your own <code style={{ fontSize: 11 }}>{current.api_key_env}</code>
            </Text>
          </Group>
          <Group gap={4} wrap="nowrap" align="center">
            <PasswordInput
              size="xs"
              value={apiKey}
              onChange={(e) => setApiKey(e.currentTarget.value)}
              placeholder="paste API key, then Save"
              style={{ flex: 1 }}
            />
            <Tooltip label="Save key locally and use it for this model">
              <Button
                size="xs"
                variant="light"
                onClick={saveAndUseKey}
                leftSection={<IconCheck size={12} />}
              >
                Save
              </Button>
            </Tooltip>
          </Group>
          <Text size="xs" c="dimmed" style={{ lineHeight: 1.4 }}>
            Stored in your browser's localStorage; the server never persists it
            to disk. Removed when you clear the field and save an empty value.
          </Text>
        </Stack>
      )}

      {current && current.api_key_present && (
        <Badge size="xs" color="green" variant="light">
          server has {current.api_key_env}
        </Badge>
      )}
    </Stack>
  );
}

function _loadKeyFor(models: ModelInfo[], modelId: string): string | null {
  const m = models.find((x) => x.id === modelId);
  if (!m) return null;
  return localStorage.getItem(STORAGE_PREFIX + m.api_key_env) || null;
}
