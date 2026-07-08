import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Textie from './ShareText.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Textie />
  </StrictMode>,
)
