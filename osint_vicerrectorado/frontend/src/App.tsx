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

import { UserPermisos } from './types';

/**
 * Permission-based route protection.
 * permisoKey: the permission key to check in user.permisos.
 * If empty string, all authenticated users can access.
 */
const PermisoRoute: React.FC<{ permisoKey?: keyof UserPermisos; children: React.ReactNode }> = ({ permisoKey, children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  
  if (permisoKey) {
    const permisos = user.permisos || getDefaultPermisos(user.rol);
    if (!permisos[permisoKey]) {
      // Redirect to first available module
      const firstAvailable = getFirstAvailableRoute(permisos);
      return <Navigate to={firstAvailable} replace />;
    }
  }
  return <>{children}</>;
};

/** Get default permisos for fallback */
const getDefaultPermisos = (rol: string): UserPermisos => {
  switch (rol) {
    case 'administrador':
      return { osint: true, posts: true, dashboards: true, nlp: true, evaluacion: true, usuarios: true, configuracion: true };
    case 'vicerrector':
      return { osint: true, posts: true, dashboards: true, nlp: true, evaluacion: true, usuarios: false, configuracion: true };
    default:
      return { osint: false, posts: false, dashboards: true, nlp: true, evaluacion: false, usuarios: false, configuracion: false };
  }
};

/** Find the first accessible route for a user */
const getFirstAvailableRoute = (permisos: UserPermisos): string => {
  if (permisos.posts) return '/dashboard/posts';
  if (permisos.osint) return '/dashboard/osint';
  if (permisos.dashboards) return '/dashboard/sentiment';
  if (permisos.nlp) return '/dashboard/nlp';
  if (permisos.evaluacion) return '/dashboard/evaluacion';
  if (permisos.configuracion) return '/dashboard/configuracion';
  return '/dashboard/ayuda';
};

/**
 * Default redirect based on permissions.
 */
const DefaultRedirect: React.FC = () => {
  const { user } = useAuth();
  const permisos = user?.permisos || getDefaultPermisos(user?.rol || 'uebu');
  const target = getFirstAvailableRoute(permisos);
  return <Navigate to={target} replace />;
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
                      <PermisoRoute permisoKey="posts">
                        <PostsDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="sentiment" element={
                      <PermisoRoute permisoKey="dashboards">
                        <SentimentDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="reputation" element={
                      <PermisoRoute permisoKey="dashboards">
                        <ReputationDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="alerts" element={
                      <PermisoRoute permisoKey="dashboards">
                        <AlertsDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="benchmarking" element={
                      <PermisoRoute permisoKey="dashboards">
                        <BenchmarkingDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="osint" element={
                      <PermisoRoute permisoKey="osint">
                        <OSINTDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="nlp" element={
                      <PermisoRoute permisoKey="nlp">
                        <NLPDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="evaluacion" element={
                      <PermisoRoute permisoKey="evaluacion">
                        <EvaluacionDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="usuarios" element={
                      <PermisoRoute permisoKey="usuarios">
                        <UsuariosDashboard />
                      </PermisoRoute>
                    } />
                    <Route path="configuracion" element={
                      <PermisoRoute permisoKey="configuracion">
                        <ConfiguracionDashboard />
                      </PermisoRoute>
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
