import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'
import { authService } from '@/services/auth'
import { api } from '@/services/api'

vi.mock('@thesysai/genui-sdk', () => ({
  C1Chat: () => <div data-testid="c1-chat">Chat Component</div>,
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('@crayonai/react-ui/styles/index.css', () => ({}))
vi.mock('@/services/auth', () => ({ authService: { getCurrentUser: vi.fn() } }))
vi.mock('@/services/api', () => ({ api: { get: vi.fn() } }))

const testUser = {
  id: 1,
  email: 'admin@test.com',
  country: 'GR',
  preferred_currency: 'EUR',
  is_active: true,
  created_at: '2025-12-28T00:00:00Z',
}

// Unsigned JWT-shaped token that AuthContext treats as unexpired
const validToken = `x.${btoa(JSON.stringify({ exp: Date.now() / 1000 + 3600 }))}.x`

const renderAt = (path: string) => {
  window.history.pushState({}, '', path)
  return render(<App />)
}

describe('App routing', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(authService.getCurrentUser).mockResolvedValue(testUser as never)
    vi.mocked(api.get).mockResolvedValue({
      data: {
        total_value: 0,
        total_cost_basis: 0,
        total_gain_loss: 0,
        total_return_pct: 0,
        holdings_count: 0,
        currency: 'EUR',
      },
    })
  })

  it('redirects unauthenticated users to the login page', async () => {
    renderAt('/dashboard')

    expect(await screen.findByRole('button', { name: /sign in|log in|login/i })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
    expect(authService.getCurrentUser).not.toHaveBeenCalled()
  })

  it('shows the shared app layout with navigation for authenticated users', async () => {
    localStorage.setItem('access_token', validToken)
    renderAt('/dashboard')

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /portfolio/i, hidden: false })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('renders chat full-screen without the app layout', async () => {
    localStorage.setItem('access_token', validToken)
    renderAt('/chat')

    expect(await screen.findByTestId('c1-chat')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()
  })
})
