<script>
  import { createEventDispatcher } from "svelte";
  export let chatHistory = [];
  const dispatch = createEventDispatcher();

  function handleExampleClick(example) {
    dispatch("executeCommand", example);
  }
</script>

<div class="chat-interface">
  <h3>💬 Chat - Whisper Flow Style</h3>
  <div class="chat-history">
    {#each chatHistory as msg}
      <div class="message" class:user={msg.role === "user"} class:assistant={msg.role === "assistant"}>
        <div class="role">{msg.role === "user" ? "You" : "OMNI V2"}</div>
        <div class="text">{msg.text}</div>
        {#if msg.chainSteps}
          <div class="chain-steps">
            {#each msg.chainSteps as step}
              <div class="chain-step">{step}</div>
            {/each}
          </div>
        {/if}
        <div class="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</div>
      </div>
    {/each}
  </div>

  <div class="examples">
    <h4>Try Chain Commands (WOW factor):</h4>
    <button on:click={() => handleExampleClick("open chrome and maximize it and go to youtube")}>
      open chrome and maximize it and go to youtube
    </button>
    <button on:click={() => handleExampleClick("open github and search for iron man")}>
      open github and search for iron man
    </button>
    <button on:click={() => handleExampleClick("turn on the lights and set temperature to 72")}>
      turn on the lights and set temperature to 72
    </button>
  </div>
</div>

<style>
  .chat-interface {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .chat-history {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 15px;
  }

  .message {
    margin: 10px 0;
    padding: 10px;
    border-radius: 8px;
  }

  .message.user {
    background: rgba(0, 200, 255, 0.2);
    border-left: 3px solid cyan;
  }

  .message.assistant {
    background: rgba(50, 255, 100, 0.1);
    border-left: 3px solid #00ff88;
  }

  .role {
    font-size: 10px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 5px;
  }

  .text {
    color: white;
    font-size: 14px;
  }

  .chain-steps {
    margin-top: 10px;
    font-size: 11px;
  }

  .chain-step {
    background: rgba(0,0,0,0.3);
    padding: 3px 5px;
    margin: 3px 0;
    border-radius: 3px;
    font-size: 10px;
  }

  .timestamp {
    font-size: 9px;
    color: rgba(255,255,255,0.3);
    margin-top: 5px;
  }

  .examples {
    border-top: 1px solid rgba(0,200,255,0.3);
    padding-top: 10px;
  }

  .examples button {
    display: block;
    width: 100%;
    margin: 5px 0;
    padding: 8px;
    background: rgba(0,200,255,0.1);
    border: 1px solid rgba(0,200,255,0.3);
    color: cyan;
    border-radius: 5px;
    cursor: pointer;
    font-size: 11px;
  }

  .examples button:hover {
    background: rgba(0,200,255,0.2);
  }
</style>
