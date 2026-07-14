'use client'
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'

const stateConfig = {
  idle: { color: 0x7DD3FC, speed: 0.001, size: 0.055 },
  listening: { color: 0x4ADE80, speed: 0.008, size: 0.09 },
  thinking: { color: 0xFB923C, speed: 0.015, size: 0.07 },
  speaking: { color: 0xC4B5FD, speed: 0.005, size: 0.08 },
  error: { color: 0xF87171, speed: 0.02, size: 0.06 }
}

export default function Orb({ state = 'idle', rms = 0 }) {
  const canvasRef = useRef(null)
  const sceneRef = useRef(null)
  const rendererRef = useRef(null)
  const particlesRef = useRef(null)
  const animationRef = useRef(null)
  
  useEffect(() => {
    if (!canvasRef.current) return
    
    const canvas = canvasRef.current
    const container = canvas.parentElement
    const width = container.clientWidth
    const height = container.clientHeight
    
    // Scene
    const scene = new THREE.Scene()
    sceneRef.current = scene
    
    const camera = new THREE.PerspectiveCamera(75, width/height, 0.1, 1000)
    camera.position.z = 5
    
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
    renderer.setSize(width, height)
    renderer.setClearColor(0x000000, 0)
    rendererRef.current = renderer
    
    // Particles - 2400 for correct spec, 1800 for performance
    const particleCount = 2000
    const geometry = new THREE.BufferGeometry()
    const positions = []
    const colors = []
    const color = new THREE.Color(0x7DD3FC)
    
    for (let i=0; i<particleCount; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 2 + Math.random() * 0.6
      positions.push(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      )
      colors.push(color.r, color.g, color.b)
    }
    
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    
    const material = new THREE.PointsMaterial({ size: 0.06, vertexColors: true, transparent: true, opacity: 0.9 })
    const particles = new THREE.Points(geometry, material)
    particlesRef.current = particles
    scene.add(particles)
    
    const animate = () => {
      animationRef.current = requestAnimationFrame(animate)
      if (particlesRef.current) {
        const cfg = stateConfig[state] || stateConfig.idle
        particlesRef.current.rotation.y += cfg.speed
        particlesRef.current.rotation.x += cfg.speed * 0.3
        if (particlesRef.current.material) {
          particlesRef.current.material.color.setHex(cfg.color)
          particlesRef.current.material.size = cfg.size + Math.sin(Date.now()*0.003) * 0.01 + rms * 2
        }
      }
      renderer.render(scene, camera)
    }
    animate()
    
    const handleResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w/h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)
    
    return () => {
      window.removeEventListener('resize', handleResize)
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
      if (rendererRef.current) rendererRef.current.dispose()
      if (geometry) geometry.dispose()
      if (material) material.dispose()
    }
  }, [])
  
  // Update on state change
  useEffect(() => {
    if (particlesRef.current && particlesRef.current.material) {
      const cfg = stateConfig[state] || stateConfig.idle
      particlesRef.current.material.color.setHex(cfg.color)
    }
  }, [state])
  
  return (
    <div className="w-[280px] h-[280px] rounded-full neu flex items-center justify-center p-3">
      <canvas ref={canvasRef} className="w-[260px] h-[260px] rounded-full" />
    </div>
  )
}
