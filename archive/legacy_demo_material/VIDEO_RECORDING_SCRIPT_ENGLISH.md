# 🎥 TEP Intelligent Fault Diagnosis System - Video Recording Script

**Target Duration**: 5-7 minutes  
**Target Audience**: Project funding reviewers  
**Core Message**: System capabilities + RAG root cause analysis + Future voice integration potential

---

## 📋 **Pre-Recording Checklist**

### **1. System Preparation**
- [ ] Close all unnecessary applications
- [ ] Clean up desktop (hide sensitive files)
- [ ] Prepare `start_all.command`
- [ ] Confirm `.env` file has API keys configured
- [ ] Test complete workflow once (ensure no errors)

### **2. Screen Recording Software Setup**
- [ ] Use QuickTime Player or OBS Studio
- [ ] Resolution: 1920x1080 (Full HD)
- [ ] Frame rate: 30fps
- [ ] Audio: Clear microphone (recommend headset mic)

### **3. Browser Preparation**
- [ ] Use Safari (your primary browser)
- [ ] Close all other tabs
- [ ] Zoom to 100% or 110% (for better viewing)
- [ ] Prepare URLs to visit

---

## 🎬 **Video Script (Segment Recording Recommended)**

---

### **Segment 1: Opening Introduction (30 seconds)**

**Screen**: Desktop → Double-click `start_all.command`

**Narration**:
> "Hello everyone. Today I'll demonstrate our **TEP Intelligent Fault Diagnosis System**. This is a real-time fault analysis platform based on industrial process simulation, integrating multiple large language models and knowledge retrieval technology."

**Actions**:
1. Double-click `start_all.command`
2. Wait for terminal window to appear (showing startup logs)

**Key Information**:
- ✅ One-command startup for all services
- ✅ Automatically starts TEP simulation, anomaly detection, LLM services in background

---

### **Segment 2: Unified Control Console (45 seconds)**

**Screen**: Browser opens http://127.0.0.1:9002

**Narration**:
> "After system startup, we enter the **Unified Control Console**. This is the central control panel for the entire system. Now I'll click the **Ultra Start 50x** button to quickly start the TEP industrial process simulation."

**Actions**:
1. Browser automatically opens control console page
2. Point to "🚀 ULTRA START (50x)" button
3. Click the button
4. Wait 1-2 seconds, show success message

**Key Information**:
- ✅ Unified console manages all services
- ✅ 50x speed simulation (accelerated demo)
- ✅ Real-time industrial process simulation startup

---




### **Segment 3: DCS Monitoring Interface (1 minute)**

**Screen**: Click "Open Fault Analysis Frontend" → Switch to frontend page

**Narration**:
> "Now we enter the **DCS Monitoring Interface**. This is the main interface for operators to monitor the industrial process in real-time."
> 
> "On the left is the **Real-time Data Panel**, displaying real-time values of 52 process variables, including temperature, pressure, flow rate, and other critical parameters."
> 
> "In the upper right is the **Anomaly Detection Status**. Currently the system is running normally, with T² statistic below threshold, showing green."
> 
> "Below is the **Multi-LLM Analysis Panel**. Since there's no anomaly yet, there are no analysis results."

**Actions**:
1. Click "Open Fault Analysis Frontend" link in console
2. Or manually open http://localhost:5173
3. Point mouse to left data panel (scroll to show)
4. Point to upper right anomaly detection area
5. Point to lower LLM analysis area (empty)

**Key Information**:
- ✅ Real-time monitoring of 52 industrial process variables
- ✅ PCA-based anomaly detection (T² statistic)
- ✅ Multi-LLM parallel analysis ready

---

### **Segment 4: TEP Simulation Explanation (45 seconds)**

**Screen**: Stay on frontend page, can switch to "Plot" tab to show trend charts

**Narration**:
> "I need to emphasize that the **TEP (Tennessee Eastman Process)** we're using is not a toy model."
> 
> "TEP is a widely recognized **standard chemical process benchmark** in industry, developed by Eastman Chemical Company, including complete chemical reaction kinetics and material balance equations."
> 
> "We use a **Fortran-compiled physics simulation engine**. All 52 signals are calculated in real-time, fully reflecting the dynamic characteristics of real industrial processes."
> 
> "This ensures the reliability of our fault diagnosis system in real industrial scenarios."

**Actions**:
1. Click "Plot" tab in top navigation
2. Show real-time trend charts (multiple curves updating dynamically)
3. Point mouse to a curve, showing real-time values

**Key Information**:
- ✅ TEP is an industry standard benchmark (not a toy)
- ✅ Fortran physics simulation engine
- ✅ 52 real-time signals reflecting real industrial processes
- ✅ Validated by academia and industry

---

### **Segment 5: Knowledge Base Construction (1 minute)**

**Screen**: Click "Assistant" tab → Knowledge Base section

**Narration**:
> "Next, I'll demonstrate our **RAG Knowledge Base System**."
> 
> "The system supports uploading PDF-format documents such as industrial manuals, operating procedures, and historical fault reports."
> 
> "After upload, the system automatically converts PDFs to Markdown format, extracts key information, and builds a vector database."
> 
> "When a fault occurs, the LLM automatically retrieves relevant knowledge, combines it with real-time sensor data, and generates precise root cause analysis."

**Actions**:
1. Click "Assistant" tab in top navigation
2. Scroll to "Knowledge Base Management" section
3. Point to "Upload PDFs" button
4. Point to existing knowledge base file list below (if any)
5. Click "Rebuild Knowledge Base" button (demo)
6. Show build success message

**Key Information**:
- ✅ Supports PDF document upload
- ✅ Automatic conversion to Markdown and vectorization
- ✅ RAG retrieval-augmented generation
- ✅ Combines historical knowledge and real-time data

---

### **Segment 6: Trigger Fault (1 minute)**

**Screen**: Return to console → Trigger IDV disturbance

**Narration**:
> "Now let's simulate an industrial fault scenario."
> 
> "I'll trigger an **IDV disturbance** in the console, simulating a feed composition change or equipment failure."
> 
> "Watch the frontend interface. You'll see anomaly detection respond first, with T² statistic exceeding threshold, and the system marking it as red anomaly status."
> 
> "Then, multiple LLM models start working in parallel, analyzing the fault cause in real-time."

**Actions**:
1. Switch back to console page (http://127.0.0.1:9002)
2. Scroll to "Disturbance Variables (IDV)" section
3. Select an IDV (e.g., IDV(1) - A/C Feed Ratio)
4. Set Step Type: "Step"
5. Set Step Time: current time + 1 minute
6. Click "Set IDV" button
7. Immediately switch back to frontend page
8. Wait for anomaly to appear (T² statistic rises, turns red)
9. Wait for LLM analysis to start (showing "Analyzing...")

**Key Information**:
- ✅ Controllable fault injection (IDV disturbance)
- ✅ Anomaly detection precedes LLM analysis
- ✅ Multi-LLM parallel real-time diagnosis

---

### **Segment 7: LLM Real-time Diagnosis (1 minute)**

**Screen**: Frontend page → Multi-LLM Analysis area

**Narration**:
> "Now you can see the system is performing **real-time root cause analysis**."
> 
> "We're using three large language models simultaneously: **Claude, Gemini, and LMStudio**. They work in parallel, cross-validating each other."
> 
> "Each model receives: First, **system prompts** containing TEP process knowledge and diagnostic methodology. Second, **real-time sensor data** including value changes before and after the anomaly. Third, **knowledge base retrieval results** with relevant historical cases and operating manuals."
> 
> "Based on this information, the LLMs generate detailed root cause analysis reports, including fault type, impact scope, and recommended actions."

**Actions**:
1. Wait for LLM analysis to complete (typically 30-60 seconds)
2. Show analysis results from all three models (Claude, Gemini, LMStudio)
3. Scroll mouse to show analysis content
4. Point to key information:
   - Fault type identification
   - Root cause analysis
   - Recommended actions

**Key Information**:
- ✅ Multi-LLM parallel validation (improves reliability)
- ✅ System prompts guide diagnostic methodology
- ✅ Combines real-time data and historical knowledge
- ✅ Generates actionable recommendations

---

### **Segment 8: Interactive Chat (1.5 minutes)**

**Screen**: Click "History" tab → Select recent analysis record → Enter interactive chat

**Narration**:
> "Beyond automatic analysis, the system also supports **interactive dialogue**."
> 
> "I'll now enter the history records and select the fault analysis we just performed."
> 
> "Clicking the **Chat** button enters the dialogue interface with the LLM."
> 
> "Operators can ask in-depth questions about this fault, such as: 'Why did the temperature rise first then fall?' or 'What would happen if I adjust this valve?'"
> 
> "The LLM will provide professional answers based on the complete context of this fault, combined with the knowledge base."
> 
> "This interactive diagnosis allows operators to deeply understand the fault mechanism, not just receive a conclusion."

**Actions**:
1. Click "History" tab in top navigation
2. Find the latest analysis record in the list
3. Click "Chat" or "View Details" button for that record
4. Enter interactive chat interface
5. Type a question in input box (e.g., "What caused the temperature spike?")
6. Click send
7. Wait for LLM response (showing streaming output)
8. Show response content

**Key Information**:
- ✅ Interactive fault diagnosis
- ✅ In-depth dialogue based on fault context
- ✅ Operators can ask professional questions
- ✅ LLM provides detailed explanations

---

### **Segment 9: Future Vision - Voice Integration (45 seconds)**

**Screen**: Stay on chat interface, or switch back to main interface

**Narration**:
> "Finally, let's talk about the **future development direction** of this system."
> 
> "All the functions you just saw are operated through a graphical interface. But in actual industrial sites, operators often need **hands-free operation**."
> 
> "We plan to integrate **voice recognition and speech synthesis modules** to achieve **hands-free operation**."
> 
> "Operators can directly say: 'System, analyze current anomaly' or 'Tell me why the reactor temperature is rising.'"
> 
> "The system will respond by voice. Operators don't need to leave the site or touch the screen to get real-time intelligent diagnostic support."
> 
> "This will greatly improve safety and efficiency at industrial sites."

**Actions**:
1. Stay on current interface
2. Can gesture to simulate voice interaction (optional)

**Key Information**:
- ✅ Future voice model integration
- ✅ Hands-free operation
- ✅ Improves on-site safety and efficiency
- ✅ Aligns with Industry 4.0 trends

---

### **Segment 10: Summary (30 seconds)**

**Screen**: Switch back to main interface or console

**Narration**:
> "To summarize, our **TEP Intelligent Fault Diagnosis System** has the following core capabilities:"
> 
> "First, **industrial-grade simulation** based on TEP standard chemical process with 52 real-time signals."
> 
> "Second, **real-time anomaly detection** based on PCA statistical model with rapid response."
> 
> "Third, **multi-LLM root cause analysis** combined with RAG knowledge base for precise diagnosis."
> 
> "Fourth, **interactive dialogue** allowing operators to explore fault mechanisms in depth."
> 
> "Fifth, **future voice integration** for hands-free intelligent diagnosis."
> 
> "Thank you for watching. I look forward to further discussion with you."

**Actions**:
1. Switch back to main interface, showing overall layout
2. Or stay on console page

**Key Information**:
- ✅ Five core capabilities summarized
- ✅ Emphasize industrial application value
- ✅ Highlight technical innovation

---

## 🎯 **Recording Tips**

### **1. Segment Recording**
- Recommend recording in 3-4 segments, then edit and merge
- Repeat each segment 2-3 times, select the best version

### **2. Narration Tips**
- Moderate speaking pace, clear pronunciation
- Avoid filler words like "um", "uh"
- Use professional terminology, but keep it concise and understandable
- Emphasize key words (e.g., "real-time", "multi-LLM", "RAG")

### **3. Screen Tips**
- Smooth mouse movement, no shaking
- Circle or point to important areas with mouse
- Wait for loading to complete before continuing (avoid blank screens)
- Pause 1-2 seconds on key data for viewers to see clearly

### **4. Time Control**
- Keep total duration to 5-7 minutes
- If over time, speed up certain segments
- If under time, linger more on key parts

---

## 📝 **Post-Recording Checklist**

- [ ] Audio is clear, no noise
- [ ] Screen is smooth, no lag
- [ ] All functions demonstrated properly
- [ ] Narration syncs with screen
- [ ] Total duration is 5-7 minutes
- [ ] All key information covered
- [ ] No sensitive information exposed (API keys, personal info)

---

## 🎬 **Editing Suggestions**

### **Tools to Use**
- **Mac**: iMovie (free, simple)
- **Professional**: Final Cut Pro, Adobe Premiere

### **Editing Points**
1. **Opening**: Add title "TEP Intelligent Fault Diagnosis System Demo"
2. **Subtitles**: Add English subtitles for key terms
3. **Annotations**: Add arrows or highlights to important areas
4. **Transitions**: Use simple fade in/out
5. **Closing**: Add contact information or project details

---

## 🚀 **Quick Recording Version (3-minute condensed)**

If you need a shorter version, record only these parts:

1. **Opening** (20 sec) - System startup
2. **DCS Interface** (40 sec) - Monitoring and anomaly detection
3. **Trigger Fault** (30 sec) - IDV disturbance + anomaly appears
4. **LLM Analysis** (40 sec) - Multi-model parallel diagnosis
5. **Interactive Chat** (30 sec) - Quick chat demo
6. **Summary** (20 sec) - Core capabilities + voice vision

**Total**: 3 minutes

---

**Good luck with your recording! 🎉**

