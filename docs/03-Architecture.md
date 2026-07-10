# OMNI Architecture

OMNI is designed as a **Closed-Loop Autonomous System**. Unlike traditional voice assistants that use a linear "If-This-Then-That" logic, OMNI uses a reasoning cycle to ensure goals are actually achieved.

## 1. The Data Flow

`User Voice` $\rightarrow$ `VAD` $\rightarrow$ `Whisper STT` $\rightarrow$ `Intent Mapper` $\rightarrow$ `OmniReasoner` $\rightarrow$ `Plugin Action` $\rightarrow$ `Observation` $\rightarrow$ `Verification` $\rightarrow$ `Correction` $\rightarrow$ `TTS/UI Feedback`

---

## 2. Component Breakdown

### A. Semantic Intent Mapper
Instead of regex, OMNI uses **Vector Embeddings**. 
- Every command example is converted into a high-dimensional vector.
- User input is converted into a vector in the same space.
- The system calculates the **Cosine Similarity**. If the similarity is $> 0.6$, the intent is matched.

### B. The Reasoning Loop (`OmniReasoner`)
The Reasoner implements a simplified version of the **ReAct (Reason + Act)** pattern:
1.  **Plan**: Define the target action based on the mapped intent.
2.  **Act**: Execute the plugin command.
3.  **Observe**: Use the plugin's `verify_action` method to check the current state of the system.
4.  **Correct**: If verification fails, apply a recovery strategy (e.g., wait, scroll, or retry).

### C. The Visual Core (`Voice Orb`)
The Orb is a real-time state machine linked to the `EventBus`:
- `RECORDING` $\rightarrow$ **Green Pulse** (Listening)
- `PROCESSING` $\rightarrow$ **Purple Glow** (Reasoning)
- `SPEAKING` $\rightarrow$ **White Expansion** (Feedback)
- `IDLE` $\rightarrow$ **Cyan Breath** (Ready)

---

## 3. Resilience Strategies

- **Hardware Fallbacks**: If CUDA fails, the system seamlessly drops to CPU `int8` without crashing.
- **TTS Fallbacks**: Kokoro $\rightarrow$ SAPI $\rightarrow$ Silent.
- **Reasoning Fallbacks**: If the autonomous loop fails after 3 retries, OMNI reports the specific failure to the user via TTS and returns to Idle.
