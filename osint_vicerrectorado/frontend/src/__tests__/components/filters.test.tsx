/**
 * Tests para componentes de filtro
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SourceFilter from '../../components/filters/SourceFilter';
import SeverityFilter, { SeverityChip } from '../../components/filters/SeverityFilter';
import { FilterProvider } from '../../contexts/FilterContext';
import { ThemeProvider } from '../../contexts/ThemeContext';
import { AlertSeverity } from '../../types';

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <ThemeProvider>
      <FilterProvider>
        {component}
      </FilterProvider>
    </ThemeProvider>
  );
};

describe('SourceFilter', () => {
  it('renders with default "all" option', () => {
    renderWithProviders(<SourceFilter />);
    
    expect(screen.getByLabelText(/fuente/i)).toBeInTheDocument();
  });

  it('renders all source options', async () => {
    renderWithProviders(<SourceFilter />);
    
    const select = screen.getByRole('combobox');
    await userEvent.click(select);

    await waitFor(() => {
      expect(screen.getByText(/todas/i)).toBeInTheDocument();
      expect(screen.getByText(/facebook/i)).toBeInTheDocument();
      expect(screen.getByText(/twitter/i)).toBeInTheDocument();
    });
  });

  it('calls onChange when source is selected', async () => {
    const onChange = jest.fn();
    renderWithProviders(<SourceFilter onChange={onChange} />);
    
    const select = screen.getByRole('combobox');
    await userEvent.click(select);
    
    await waitFor(() => {
      const twitterOption = screen.getByRole('option', { name: /twitter/i });
      fireEvent.click(twitterOption);
    });

    expect(onChange).toHaveBeenCalledWith('twitter');
  });
});

describe('SeverityFilter', () => {
  it('renders with default "all" option', () => {
    renderWithProviders(<SeverityFilter />);
    
    expect(screen.getByLabelText(/severidad/i)).toBeInTheDocument();
  });

  it('renders all severity options', async () => {
    renderWithProviders(<SeverityFilter />);
    
    const select = screen.getByRole('combobox');
    await userEvent.click(select);

    await waitFor(() => {
      expect(screen.getByText(/todas/i)).toBeInTheDocument();
      expect(screen.getByText(/crítica/i)).toBeInTheDocument();
      expect(screen.getByText(/alta/i)).toBeInTheDocument();
      expect(screen.getByText(/media/i)).toBeInTheDocument();
      expect(screen.getByText(/baja/i)).toBeInTheDocument();
    });
  });
});

describe('SeverityChip', () => {
  it('renders critical severity with correct color', () => {
    render(
      <ThemeProvider>
        <SeverityChip severity={'critica' as AlertSeverity} />
      </ThemeProvider>
    );
    
    const chip = screen.getByText(/crítica/i);
    expect(chip).toBeInTheDocument();
  });

  it('renders high severity with correct label', () => {
    render(
      <ThemeProvider>
        <SeverityChip severity={'alta' as AlertSeverity} />
      </ThemeProvider>
    );
    
    expect(screen.getByText(/alta/i)).toBeInTheDocument();
  });

  it('renders medium severity with correct label', () => {
    render(
      <ThemeProvider>
        <SeverityChip severity={'media' as AlertSeverity} />
      </ThemeProvider>
    );
    
    expect(screen.getByText(/media/i)).toBeInTheDocument();
  });

  it('renders low severity with correct label', () => {
    render(
      <ThemeProvider>
        <SeverityChip severity={'baja' as AlertSeverity} />
      </ThemeProvider>
    );
    
    expect(screen.getByText(/baja/i)).toBeInTheDocument();
  });

  it('applies small size when specified', () => {
    render(
      <ThemeProvider>
        <SeverityChip severity={'alta' as AlertSeverity} size="small" />
      </ThemeProvider>
    );
    
    const chip = screen.getByText(/alta/i).closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-sizeSmall');
  });

  it('applies custom className', () => {
    render(
      <ThemeProvider>
        <SeverityChip severity={'baja' as AlertSeverity} className="custom-class" />
      </ThemeProvider>
    );
    
    const chip = screen.getByText(/baja/i).closest('.MuiChip-root');
    expect(chip).toHaveClass('custom-class');
  });
});
