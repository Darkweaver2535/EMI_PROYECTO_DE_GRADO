/**
 * Tests para componentes comunes
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import ErrorBoundary from '../../components/common/ErrorBoundary';
import { ThemeProvider } from '../../contexts/ThemeContext';

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider>
      {component}
    </ThemeProvider>
  );
};

describe('LoadingSpinner', () => {
  it('renders loading spinner', () => {
    renderWithTheme(<LoadingSpinner />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays custom message', () => {
    renderWithTheme(<LoadingSpinner message="Cargando datos..." />);
    expect(screen.getByText('Cargando datos...')).toBeInTheDocument();
  });

  it('renders with fullscreen mode', () => {
    const { container } = renderWithTheme(<LoadingSpinner fullScreen />);
    expect(container.firstChild).toHaveStyle({ position: 'fixed' });
  });

  it('renders small size spinner', () => {
    const { container } = renderWithTheme(<LoadingSpinner size="small" />);
    const spinner = container.querySelector('.MuiCircularProgress-root');
    expect(spinner).toBeInTheDocument();
  });

  it('renders large size spinner', () => {
    const { container } = renderWithTheme(<LoadingSpinner size="large" />);
    const spinner = container.querySelector('.MuiCircularProgress-root');
    expect(spinner).toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('renders default message', () => {
    renderWithTheme(<EmptyState />);
    expect(screen.getByText(/no hay datos/i)).toBeInTheDocument();
  });

  it('renders custom title', () => {
    renderWithTheme(<EmptyState title="Sin resultados" />);
    expect(screen.getByText('Sin resultados')).toBeInTheDocument();
  });

  it('renders custom description', () => {
    renderWithTheme(<EmptyState description="Intenta cambiar los filtros" />);
    expect(screen.getByText('Intenta cambiar los filtros')).toBeInTheDocument();
  });

  it('renders action button when provided', () => {
    const handleAction = jest.fn();
    renderWithTheme(
      <EmptyState 
        actionLabel="Recargar" 
        onAction={handleAction} 
      />
    );
    
    const button = screen.getByText('Recargar');
    expect(button).toBeInTheDocument();
    
    fireEvent.click(button);
    expect(handleAction).toHaveBeenCalled();
  });

  it('renders custom icon when provided', () => {
    renderWithTheme(
      <EmptyState icon={<span data-testid="custom-icon">🔍</span>} />
    );
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });
});

// Test component that throws an error
const ErrorComponent: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>Child component</div>;
};

describe('ErrorBoundary', () => {
  // Suppress console.error for error boundary tests
  const originalError = console.error;
  beforeAll(() => {
    console.error = jest.fn();
  });
  afterAll(() => {
    console.error = originalError;
  });

  it('renders children when no error', () => {
    renderWithTheme(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('renders error UI when child throws', () => {
    renderWithTheme(
      <ErrorBoundary>
        <ErrorComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(screen.getByText(/algo salió mal/i)).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    renderWithTheme(
      <ErrorBoundary fallback={<div>Custom error message</div>}>
        <ErrorComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Custom error message')).toBeInTheDocument();
  });

  it('calls onError callback when error occurs', () => {
    const handleError = jest.fn();
    
    renderWithTheme(
      <ErrorBoundary onError={handleError}>
        <ErrorComponent shouldThrow />
      </ErrorBoundary>
    );
    
    expect(handleError).toHaveBeenCalled();
  });

  it('allows retry after error', async () => {
    renderWithTheme(
      <ErrorBoundary>
        <ErrorComponent shouldThrow />
      </ErrorBoundary>
    );
    
    // Verify error state
    expect(screen.getByText(/algo salió mal/i)).toBeInTheDocument();
    
    // Find and click retry button
    const retryButton = screen.getByRole('button', { name: /reintentar/i });
    expect(retryButton).toBeInTheDocument();
  });
});
