<script>
  export let state = "idle";
  import { onMount } from "svelte";
  
  let canvas;
  let ctx;
  let particles = [];
  let animationId;
  let pulseVal = 0;
  let pulseDir = 1;

  const stateColors = {
    idle: "rgba(0, 200, 255, 0.8)",
    listening: "rgba(50, 255, 100, 0.9)",
    thinking: "rgba(255, 136, 0, 0.9)",
    speaking: "rgba(255, 255, 255, 0.9)",
    error: "rgba(255, 0, 68, 0.9)"
  };

  onMount(() => {
    ctx = canvas.getContext("2d");
    canvas.width = 200;
    canvas.height = 200;
    
    // Create 100 particles for demo (2400 in full Three.js version)
    for (let i = 0; i < 100; i++) {
      particles.push({
        angle: Math.random() * Math.PI * 2,
        radius: 60 + Math.random() * 20,
        speed: 0.01 + Math.random() * 0.02,
        size: 2 + Math.random() * 3
      });
    }
    
    animate();
    
    return () => cancelAnimationFrame(animationId);
  });

  function animate() {
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    pulseVal += 0.05 * pulseDir;
    if (pulseVal > 1 || pulseVal < 0) pulseDir *= -1;
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const baseRadius = 60;
    const pulse = state === "listening" ? 10 * pulseVal : state === "thinking" ? 5 * Math.sin(pulseVal * 5) : 0;
    const radius = baseRadius + pulse;
    
    // Draw orb glow
    const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
    gradient.addColorStop(0, stateColors[state] || stateColors.idle);
    gradient.addColorStop(1, "rgba(0,0,0,0)");
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fill();
    
    // Draw particles orbiting
    particles.forEach(p => {
      p.angle += p.speed * (state === "thinking" ? 2 : state === "listening" ? 1.5 : 1);
      const x = centerX + Math.cos(p.angle) * p.radius;
      const y = centerY + Math.sin(p.angle) * p.radius;
      
      ctx.fillStyle = stateColors[state] || stateColors.idle;
      ctx.beginPath();
      ctx.arc(x, y, p.size, 0, Math.PI * 2);
      ctx.fill();
    });
    
    // Center text
    ctx.fillStyle = "white";
    ctx.font = "bold 16px Arial";
    ctx.textAlign = "center";
    ctx.fillText("OMNI", centerX, centerY - 5);
    ctx.font = "12px Arial";
    ctx.fillText("V2", centerX, centerY + 10);
    
    animationId = requestAnimationFrame(animate);
  }

  $: if (ctx) {
    // React to state change
  }
</script>

<canvas bind:this={canvas} class="orb-canvas"></canvas>

<style>
  .orb-canvas {
    width: 200px;
    height: 200px;
    border-radius: 50%;
  }
</style>
