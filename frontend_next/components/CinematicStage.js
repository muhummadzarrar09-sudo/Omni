'use client'
import { useEffect, useRef } from 'react'

export default function CinematicStage({ state = 'idle', rms = 0 }) {
  const canvasRef = useRef(null)
  
  // Animation state targets for smooth morphing:
  // morphProgress: 0.0 = Line (Listening/Speaking/Idle), 1.0 = Circle/Orb (Thinking)
  const animState = useRef({
    morphProgress: 0.0,
    targetMorph: 0.0,
    angle: 0.0,
    springRms: 0.0,
    particles: []
  })

  useEffect(() => {
    // Init 150 points along the line / circumference
    const pCount = 180
    const particles = []
    for (let i = 0; i < pCount; i++) {
      particles.push({
        index: i,
        t: i / (pCount - 1), // 0 to 1
        baseRadius: 110,
        amp: 0,
        phase: Math.random() * Math.PI * 2,
        freq: 2 + Math.random() * 6
      })
    }
    animState.current.particles = particles
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animationFrameId

    const render = () => {
      const { width, height } = canvas
      ctx.clearRect(0, 0, width, height)

      // Determine target morph based on state
      // Line: listening, speaking, idle -> 0.0
      // Circle/Orb: thinking -> 1.0
      if (state === 'thinking') {
        animState.current.targetMorph = 1.0
      } else {
        animState.current.targetMorph = 0.0
      }

      // Smooth elastic interpolation (Spring/Morph behavior)
      const morphDiff = animState.current.targetMorph - animState.current.morphProgress
      animState.current.morphProgress += morphDiff * 0.08 // Smooth transition

      // Smooth RMS damping - ZERO vibration when idle, muted, or silent room ambient
      let targetRms = 0.0
      if (state === 'speaking') {
        targetRms = Math.max(rms, 0.035)
      } else if (state === 'listening') {
        // Strict threshold: ignore ambient fan noise < 0.018 so the line stays dead flat until real speech hits!
        targetRms = rms > 0.018 ? (rms - 0.018) * 2.2 : 0.0
      } else if (state === 'thinking') {
        targetRms = 0.005 // Subtle smooth rotating field for thinking
      } else {
        targetRms = 0.0 // Dead flat crisp laser line when idle
      }
      
      animState.current.springRms += (targetRms - animState.current.springRms) * 0.18
      animState.current.angle += (state === 'thinking' ? 0.04 : 0.015)

      const centerX = width / 2
      const centerY = height / 2
      const lineLength = Math.min(width * 0.65, 520)
      const startX = centerX - lineLength / 2

      const morph = animState.current.morphProgress
      const currentRms = animState.current.springRms
      const time = animState.current.angle

      ctx.save()
      
      // Draw outer glowing aura / field when thinking or active
      if (morph > 0.1 || state !== 'idle') {
        const gradRadius = 140 + currentRms * 300
        const auraGrad = ctx.createRadialGradient(centerX, centerY, 10, centerX, centerY, gradRadius)
        if (state === 'listening') {
          auraGrad.addColorStop(0, 'rgba(56, 189, 248, 0.22)') // Sky Blue
          auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
        } else if (state === 'thinking') {
          auraGrad.addColorStop(0, 'rgba(251, 146, 60, 0.28)') // Orange/Amber pulsing orb field
          auraGrad.addColorStop(0.5, 'rgba(249, 115, 22, 0.1)')
          auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
        } else if (state === 'speaking') {
          auraGrad.addColorStop(0, 'rgba(192, 132, 252, 0.25)') // Purple/Violet
          auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
        } else {
          auraGrad.addColorStop(0, 'rgba(125, 211, 252, 0.08)')
          auraGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
        }
        ctx.fillStyle = auraGrad
        ctx.fillRect(0, 0, width, height)
      }

      // Main line / orb stroke
      ctx.beginPath()
      const pts = animState.current.particles
      
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i]
        
        // Line coordinates (Horizontal centered)
        const lineX = startX + p.t * lineLength
        
        // Elastic waveform amplitude: higher near center of line
        const envelope = Math.sin(p.t * Math.PI)
        const waveOffset = Math.sin(time * p.freq + p.phase) * currentRms * 140 * envelope
        const lineY = centerY + waveOffset

        // Orb/Circle coordinates (Rotating field around center)
        const orbAngle = time + p.t * Math.PI * 2
        const orbRadius = 105 + Math.sin(orbAngle * 4 + time * 2) * currentRms * 60
        const orbX = centerX + Math.cos(orbAngle) * orbRadius
        const orbY = centerY + Math.sin(orbAngle) * orbRadius

        // Interpolate between Line (0.0) and Orb (1.0)
        const x = lineX * (1 - morph) + orbX * morph
        const y = lineY * (1 - morph) + orbY * morph

        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }

      // If close to circle morph, close path for seamless loop
      if (morph > 0.85) {
        ctx.closePath()
      }

      // Set stroke styles according to state
      ctx.lineWidth = 3 + currentRms * 12
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      if (state === 'listening') {
        ctx.strokeStyle = '#38BDF8' // Cyan / Sky Blue
        ctx.shadowColor = '#0EA5E9'
      } else if (state === 'thinking') {
        ctx.strokeStyle = '#FB923C' // Amber / Orange
        ctx.shadowColor = '#F97316'
      } else if (state === 'speaking') {
        ctx.strokeStyle = '#C084FC' // Violet / Purple
        ctx.shadowColor = '#A855F7'
      } else {
        ctx.strokeStyle = '#7DD3FC' // Idle soft cyan
        ctx.shadowColor = '#38BDF8'
      }
      
      ctx.shadowBlur = 18 + currentRms * 40
      ctx.stroke()

      // Secondary core glow layer
      ctx.lineWidth = 1.5
      ctx.strokeStyle = '#FFFFFF'
      ctx.shadowBlur = 8
      ctx.stroke()

      ctx.restore()
      animationFrameId = requestAnimationFrame(render)
    }

    // Resize observer
    const handleResize = () => {
      canvas.width = canvas.parentElement.clientWidth
      canvas.height = canvas.parentElement.clientHeight
    }
    handleResize()
    window.addEventListener('resize', handleResize)

    render()

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', handleResize)
    }
  }, [state, rms])

  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden select-none">
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  )
}
