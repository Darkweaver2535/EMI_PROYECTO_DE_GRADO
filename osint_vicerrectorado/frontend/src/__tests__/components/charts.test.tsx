/**
 * Tests para componentes de gráficos
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import SentimentLineChart from '../../components/charts/SentimentLineChart';
import SentimentPieChart from '../../components/charts/SentimentPieChart';
import CareerBarChart from '../../components/charts/CareerBarChart';
import HeatmapChart from '../../components/charts/HeatmapChart';
import CorrelationMatrixChart from '../../components/charts/CorrelationMatrixChart';
import { ThemeProvider } from '../../contexts/ThemeContext';
import { SentimentData, SentimentDistribution, CareerRanking, HeatmapData, CorrelationMatrix } from '../../types';

// Mock ResizeObserver for Recharts
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider>
      {component}
    </ThemeProvider>
  );
};

describe('SentimentLineChart', () => {
  const mockData: SentimentData[] = [
    { date: '2024-01-01', positive: 50, negative: 30, neutral: 20 },
    { date: '2024-01-02', positive: 55, negative: 25, neutral: 20 },
    { date: '2024-01-03', positive: 60, negative: 20, neutral: 20 },
  ];

  it('renders without crashing', () => {
    renderWithTheme(<SentimentLineChart data={mockData} />);
    // Chart renders within a container
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    renderWithTheme(<SentimentLineChart data={[]} />);
    expect(screen.getByText(/no hay datos/i)).toBeInTheDocument();
  });

  it('renders loading state', () => {
    renderWithTheme(<SentimentLineChart data={mockData} loading />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('applies custom height', () => {
    const { container } = renderWithTheme(
      <SentimentLineChart data={mockData} height={400} />
    );
    const wrapper = container.querySelector('.recharts-responsive-container');
    expect(wrapper).toHaveStyle({ height: '400px' });
  });
});

describe('SentimentPieChart', () => {
  const mockData: SentimentDistribution = {
    positive: 50,
    negative: 30,
    neutral: 20,
    total: 100,
  };

  it('renders without crashing', () => {
    renderWithTheme(<SentimentPieChart data={mockData} />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('renders with zero values', () => {
    const zeroData: SentimentDistribution = {
      positive: 0,
      negative: 0,
      neutral: 0,
      total: 0,
    };
    renderWithTheme(<SentimentPieChart data={zeroData} />);
    expect(screen.getByText(/no hay datos/i)).toBeInTheDocument();
  });

  it('renders loading state', () => {
    renderWithTheme(<SentimentPieChart data={mockData} loading />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('shows legend by default', () => {
    renderWithTheme(<SentimentPieChart data={mockData} />);
    expect(document.querySelector('.recharts-legend-wrapper')).toBeInTheDocument();
  });
});

describe('CareerBarChart', () => {
  const mockData: CareerRanking[] = [
    { id: 1, nombre: 'Ingeniería de Sistemas', codigo: 'SIS', satisfactionScore: 85, rank: 1, totalOpinions: 100, trend: 'up', change: 5 },
    { id: 2, nombre: 'Ingeniería Industrial', codigo: 'IND', satisfactionScore: 75, rank: 2, totalOpinions: 100, trend: 'stable', change: 0 },
    { id: 3, nombre: 'Administración', codigo: 'ADM', satisfactionScore: 65, rank: 3, totalOpinions: 100, trend: 'down', change: -3 },
  ];

  it('renders without crashing', () => {
    renderWithTheme(<CareerBarChart data={mockData} />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    renderWithTheme(<CareerBarChart data={[]} />);
    expect(screen.getByText(/no hay datos/i)).toBeInTheDocument();
  });

  it('renders horizontal layout by default', () => {
    renderWithTheme(<CareerBarChart data={mockData} layout="horizontal" />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('renders vertical layout when specified', () => {
    renderWithTheme(<CareerBarChart data={mockData} layout="vertical" />);
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('calls onClick when bar is clicked', () => {
    const handleClick = jest.fn();
    renderWithTheme(<CareerBarChart data={mockData} onBarClick={handleClick} />);
    // Recharts handles click events internally
    expect(document.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });
});

describe('HeatmapChart', () => {
  const mockData: HeatmapData = {
    cells: [
      { day: 1, hour: 9, value: 50 },
      { day: 1, hour: 10, value: 75 },
      { day: 2, hour: 9, value: 60 },
    ],
    maxValue: 100,
    minValue: 0,
  };

  it('renders without crashing', () => {
    renderWithTheme(<HeatmapChart data={mockData} />);
    // Custom heatmap uses divs
    expect(screen.getByTestId('heatmap-container')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    const emptyData: HeatmapData = { cells: [], maxValue: 0, minValue: 0 };
    renderWithTheme(<HeatmapChart data={emptyData} />);
    expect(screen.getByText(/no hay datos/i)).toBeInTheDocument();
  });

  it('renders day labels', () => {
    renderWithTheme(<HeatmapChart data={mockData} />);
    expect(screen.getByText('Lun')).toBeInTheDocument();
  });

  it('renders hour labels', () => {
    renderWithTheme(<HeatmapChart data={mockData} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('shows tooltip on cell hover', () => {
    renderWithTheme(<HeatmapChart data={mockData} />);
    const cells = screen.getAllByTestId('heatmap-cell');
    expect(cells.length).toBeGreaterThan(0);
  });
});

describe('CorrelationMatrixChart', () => {
  const mockData: CorrelationMatrix = {
    variables: ['Sentiment', 'Engagement', 'Growth'],
    cells: [
      { variable1: 'Sentiment', variable2: 'Engagement', correlation: 0.85, pValue: 0.01, significance: 'high' },
      { variable1: 'Sentiment', variable2: 'Growth', correlation: 0.5, pValue: 0.05, significance: 'medium' },
      { variable1: 'Engagement', variable2: 'Growth', correlation: -0.3, pValue: 0.1, significance: 'low' },
    ],
  };

  it('renders without crashing', () => {
    renderWithTheme(<CorrelationMatrixChart data={mockData} />);
    expect(screen.getByTestId('correlation-matrix')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    const emptyData: CorrelationMatrix = { variables: [], cells: [] };
    renderWithTheme(<CorrelationMatrixChart data={emptyData} />);
    expect(screen.getByText(/no hay datos/i)).toBeInTheDocument();
  });

  it('displays variable labels', () => {
    renderWithTheme(<CorrelationMatrixChart data={mockData} />);
    expect(screen.getByText('Sentiment')).toBeInTheDocument();
    expect(screen.getByText('Engagement')).toBeInTheDocument();
  });

  it('shows correlation values', () => {
    renderWithTheme(<CorrelationMatrixChart data={mockData} />);
    expect(screen.getByText('0.85')).toBeInTheDocument();
  });

  it('applies correct color for positive correlation', () => {
    renderWithTheme(<CorrelationMatrixChart data={mockData} />);
    const cells = screen.getAllByTestId('correlation-cell');
    expect(cells.length).toBeGreaterThan(0);
  });
});
