import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

const root = document.getElementById('root')
if (!root) throw new Error('No se encuentra el elemento raíz')

createRoot(root).render(
  <StrictMode>
    <p>Joyería Blanco</p>
  </StrictMode>,
)
