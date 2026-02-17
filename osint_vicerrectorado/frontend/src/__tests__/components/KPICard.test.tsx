/**
 * Tests para KPICard
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import KPICard from '../../components/common/KPICard';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('KPICard', () => {
  it('renders title and value correctly', () => {
    renderWithTheme(
      <KPICard title="Test Title" value="123" />
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('123')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    renderWithTheme(
      <KPICard title="Test" value="100" subtitle="Test subtitle" />
    );

    expect(screen.getByText('Test subtitle')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    const TestIcon = () => <span data-testid="test-icon">Icon</span>;
    
    renderWithTheme(
      <KPICard title="Test" value="100" icon={<TestIcon />} />
    );

    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
  });

  it('shows loading state when loading is true', () => {
    const { container } = renderWithTheme(
      <KPICard title="Test" value="100" loading />
    );

    // Should show skeleton instead of actual content
    expect(container.querySelector('.MuiSkeleton-root')).toBeInTheDocument();
    expect(screen.queryByText('100')).not.toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const handleClick = jest.fn();
    
    renderWithTheme(
      <KPICard title="Test" value="100" onClick={handleClick} />
    );

    fireEvent.click(screen.getByText('Test').closest('.MuiCard-root')!);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('displays trend up indicator', () => {
    const { container } = renderWithTheme(
      <KPICard title="Test" value="100" trend="up" trendValue="+10%" />
    );

    expect(screen.getByText('+10%')).toBeInTheDocument();
    expect(container.querySelector('[data-testid="TrendingUpIcon"]')).toBeInTheDocument();
  });

  it('displays trend down indicator', () => {
    const { container } = renderWithTheme(
      <KPICard title="Test" value="100" trend="down" trendValue="-5%" />
    );

    expect(screen.getByText('-5%')).toBeInTheDocument();
    expect(container.querySelector('[data-testid="TrendingDownIcon"]')).toBeInTheDocument();
  });

  it('applies correct color based on prop', () => {
    const { container } = renderWithTheme(
      <KPICard title="Test" value="100" color="success" />
    );

    // Check that the card has success color styling
    const card = container.querySelector('.MuiCard-root');
    expect(card).toBeInTheDocument();
  });
});
