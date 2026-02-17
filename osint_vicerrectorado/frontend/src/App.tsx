/**
 * Componente principal App
 * Sistema OSINT EMI - Sprint 4
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, FilterProvider, ThemeProvider } from './contexts';
import { LoadingSpinner, ErrorBoundary } from './components/common';

// Lazy loading de páginas
const Login = lazy(() => import('./pages/Login'));
const DashboardLayout = lazy(() => import('./pages/DashboardLayout'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Lazy loading de dashboards
const PostsDashboard = lazy(() => import('./components/dashboards/PostsDashboard'));
const SentimentDashboard = lazy(() => import('./components/dashboards/SentimentDashboard'));
const ReputationDashboard = lazy(() => import('./components/dashboards/ReputationDashboard'));
const AlertsDashboard = lazy(() => import('./components/dashboards/AlertsDashboard'));
const BenchmarkingDashboard = lazy(() => import('./components/dashboards/BenchmarkingDashboard'));

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <FilterProvider>
            <BrowserRouter>
              <Suspense fallback={<LoadingSpinner fullScreen message="Cargando aplicación..." />}>
                <Routes>
                  {/* Ruta de login */}
                  <Route path="/login" element={<Login />} />
                  
                  {/* Rutas protegidas del dashboard */}
                  <Route path="/dashboard" element={<DashboardLayout />}>
                    <Route index element={<Navigate to="posts" replace />} />
                    <Route path="posts" element={<PostsDashboard />} />
                    <Route path="sentiment" element={<SentimentDashboard />} />
                    <Route path="reputation" element={<ReputationDashboard />} />
                    <Route path="alerts" element={<AlertsDashboard />} />
                    <Route path="benchmarking" element={<BenchmarkingDashboard />} />
                  </Route>
                  
                  {/* Redirección de raíz a Posts (vista principal) */}
                  <Route path="/" element={<Navigate to="/dashboard/posts" replace />} />
                  
                  {/* Página 404 */}
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </BrowserRouter>
          </FilterProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
