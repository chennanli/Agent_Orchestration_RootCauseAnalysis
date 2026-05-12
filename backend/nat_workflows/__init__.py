"""NeMo Agent Toolkit (NAT) workflow definitions for the TEP RCA demo.

The Python module `nat_tep_plugin` registers the read-only diagnostic tools
under their `_type` names used in `tep_rca_workflow.yml`. Importing this
package will silently skip registration when NAT is not installed, so the
package remains safe to import in the legacy demo path.
"""

from importlib import import_module
import logging

logger = logging.getLogger(__name__)

try:
    import_module("backend.nat_workflows.nat_tep_plugin")
except Exception as exc:  # pragma: no cover
    logger.info("NAT plugin not registered (NAT extras likely missing): %s", exc)
