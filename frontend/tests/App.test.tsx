import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'

describe('App', () => {
  it('renderiza o título principal', () => {
    render(
      <MemoryRouter initialEntries={['/fundos/cadastro']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText('Analisador de Fundos')).toBeTruthy()
  })
})
