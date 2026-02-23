/**
 * Componente principal App
 * Sistema OSINT EMI - Sprint 4
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, FilterProvider, ThemeProvider, useAuth } from './contexts';
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
const OSINTDashboard = lazy(() => import('./components/dashboards/OSINTDashboard'));
const NLPDashboard = lazy(() => import('./components/dashboards/NLPDashboard'));
const EvaluacionDashboard = lazy(() => import('./components/dashboards/EvaluacionDashboard'));
const UsuariosDashboard = lazy(() => import('./components/dashboards/UsuariosDashboard'));
const ConfiguracionDashboard = lazy(() => import('./components/dashboards/ConfiguracionDashboard'));
const AyudaDashboard = lazy(() => import('./components/dashboards/AyudaDashboard'));

/**
 * Role-based route protection.
 * allowedRoles: roles that can access. If empty, all authenticated users can.
 */
const RoleRoute: React.FC<{ allowedRoles: string[]; children: React.ReactNode }> = ({ allowedRoles, children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles.length > 0 && !allowedRoles.includes(user.rol)) {
    return <Navigate to="/dashboard/sentiment" replace />;
  }
  return <>{children}</>;
};

/**
 * Default redirect based on role.
 * Admin/Vicerrector go to posts, UEBU goes to sentiment (Analisis AI).
 */
const DefaultRedirect: React.FC = () => {
  const { user } = useAuth();
  if (user?.rol === 'uebu') {
    return <Navigate to="sentiment" replace />;
  }
  return <Navigate to="posts" replace />;
};

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
                    <Route index element={<DefaultRedirect />} />
                    <Route path="posts" element={
                      <RoleRoute allowedRoles={['administrador', 'vicerrector']}>
                        <PostsDashboard />
                      </RoleRoute>
                    } />
                    <Route path="sentiment" element={<SentimentDashboard />} />
                    <Route path="reputation" element={<ReputationDashboard />} />
                    <Route path="alerts" element={<AlertsDashboard />} />
                    <Route path="benchmarking" element={<BenchmarkingDashboard />} />
                    <Route path="osint" element={
                      <RoleRoute allowedRoles={['administrador', 'vicerrector']}>
                        <OSINTDashboard />
                      </RoleRoute>
                    } />
                    <Route path="nlp" element={<NLPDashboard />} />
                    <Route path="evaluacion" element={
                      <RoleRoute allowedRoles={['administrador', 'vicerrector']}>
                        <EvaluacionDashboard />
                      </RoleRoute>
                    } />
                    <Route path="usuarios" element={
                      <RoleRoute allowedRoles={['administrador']}>
                        <UsuariosDashboard />
                      </RoleRoute>
                    } />
                    <Route path="configuracion" element={
                      <RoleRoute allowedRoles={['administrador', 'vicerrector']}>
                        <ConfiguracionDashboard />
                      </RoleRoute>
                    } />
                    <Route path="ayuda" element={<AyudaDashboard />} />
                  </Route>
                  
                  {/* Redireccion de raiz al dashboard */}
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  
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
