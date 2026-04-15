import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

// Mock the external UI components
vi.mock('@thesysai/genui-sdk', () => ({
  C1Chat: () => <div data-testid="c1-chat">Chat Component</div>,
  ThemeProvider: ({ children, mode }: { children: React.ReactNode; mode: string }) => (
    <div data-testid="theme-provider" data-mode={mode}>
      {children}
    </div>
  ),
}))

// Mock the CSS imports
vi.mock('@crayonai/react-ui/styles/index.css', () => ({}))
vi.mock('../App.css', () => ({}))

describe('App Component', () => {
  it('renders the app container', () => {
    render(<App />)
    const container = document.querySelector('.app-container')
    expect(container).toBeInTheDocument()
  })

  it('renders ThemeProvider with dark mode', () => {
    render(<App />)
    const themeProvider = screen.getByTestId('theme-provider')
    expect(themeProvider).toBeInTheDocument()
    expect(themeProvider).toHaveAttribute('data-mode', 'dark')
  })

  it('renders C1Chat component', () => {
    render(<App />)
    const chatComponent = screen.getByTestId('c1-chat')
    expect(chatComponent).toBeInTheDocument()
  })

  it('mounts without errors', () => {
    expect(() => render(<App />)).not.toThrow()
  })

  it('has proper component hierarchy', () => {
    const { container } = render(<App />)

    // Check structure: app-container > ThemeProvider > C1Chat
    const appContainer = container.querySelector('.app-container')
    expect(appContainer).toBeInTheDocument()

    const themeProvider = screen.getByTestId('theme-provider')
    expect(appContainer).toContainElement(themeProvider)

    const chatComponent = screen.getByTestId('c1-chat')
    expect(themeProvider).toContainElement(chatComponent)
  })
})
