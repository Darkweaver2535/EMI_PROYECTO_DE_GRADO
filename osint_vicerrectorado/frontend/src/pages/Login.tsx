/**
 * Página de Login
 * Sistema SADUTO - Analítica Digital EMI
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
  Link,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email as EmailIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts';

// Paleta institucional
const COLORS = {
  blue: '#0D47A1',
  blueDark: '#002171',
  blueLight: '#5472D3',
  yellow: '#FFD700',
  yellowDark: '#C7A600',
  white: '#ffffff',
};

interface LocationState {
  from?: { pathname: string };
}

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const from = (location.state as LocationState)?.from?.pathname || '/dashboard/sentiment';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim()) {
      setLocalError('Por favor ingrese su correo electrónico');
      return;
    }

    if (!password) {
      setLocalError('Por favor ingrese su contraseña');
      return;
    }

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      // Error ya manejado por el contexto
    }
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Fondo con imagen */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: 'url(/assets/fondo.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          '&::after': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `linear-gradient(135deg, rgba(13, 71, 161, 0.82) 0%, rgba(0, 33, 113, 0.88) 100%)`,
          },
        }}
      />

      {/* Contenido del login */}
      <Box
        sx={{
          position: 'relative',
          zIndex: 1,
          width: '100%',
          maxWidth: 440,
          mx: 2,
        }}
      >
        <Card
          sx={{
            borderRadius: 3,
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
            backdropFilter: 'blur(10px)',
            overflow: 'visible',
          }}
        >
          <CardContent sx={{ p: 4, pt: 5 }}>
            {/* Logo y título */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Box
                component="img"
                src="/assets/saduto-logo.png"
                alt="SADUTO Logo"
                sx={{
                  height: 190,
                  mb: 2,
                  filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.15))',
                }}
                onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
              <Typography
                variant="h4"
                component="h1"
                fontWeight={700}
                sx={{ color: COLORS.blue }}
              >
                SISTEMA DE ANALÍTICA DE DATOS UTILIZANDO TÉCNICAS OPEN SOURCE INTELLIGENCE
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              </Typography>
              <Box
                sx={{
                  width: 60,
                  height: 3,
                  background: `linear-gradient(90deg, ${COLORS.blue}, ${COLORS.yellow})`,
                  borderRadius: 2,
                  mx: 'auto',
                  mt: 1.5,
                }}
              />
            </Box>

            {/* Errores */}
            {(error || localError) && (
              <Alert
                severity="error"
                sx={{ mb: 3, borderRadius: 2 }}
                onClose={() => {
                  clearError();
                  setLocalError(null);
                }}
              >
                {localError || error}
              </Alert>
            )}

            {/* Formulario */}
            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Correo electrónico"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                margin="normal"
                autoComplete="email"
                autoFocus
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <EmailIcon sx={{ color: COLORS.blue }} />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '&:hover fieldset': { borderColor: COLORS.blue },
                    '&.Mui-focused fieldset': { borderColor: COLORS.blue },
                  },
                  '& .MuiInputLabel-root.Mui-focused': { color: COLORS.blue },
                }}
              />

              <TextField
                fullWidth
                label="Contraseña"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                margin="normal"
                autoComplete="current-password"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockIcon sx={{ color: COLORS.blue }} />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={handleTogglePassword}
                        edge="end"
                        aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '&:hover fieldset': { borderColor: COLORS.blue },
                    '&.Mui-focused fieldset': { borderColor: COLORS.blue },
                  },
                  '& .MuiInputLabel-root.Mui-focused': { color: COLORS.blue },
                }}
              />

              <Box sx={{ textAlign: 'right', mt: 1 }}>
                <Link
                  href="#"
                  variant="body2"
                  underline="hover"
                  sx={{ color: COLORS.blue }}
                  onClick={(e) => {
                    e.preventDefault();
                  }}
                >
                  ¿Olvidaste tu contraseña?
                </Link>
              </Box>

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={isLoading}
                sx={{
                  mt: 3,
                  mb: 2,
                  py: 1.5,
                  bgcolor: COLORS.blue,
                  fontWeight: 600,
                  fontSize: '1rem',
                  letterSpacing: 0.5,
                  boxShadow: '0 4px 14px rgba(13, 71, 161, 0.4)',
                  '&:hover': {
                    bgcolor: COLORS.blueDark,
                    boxShadow: '0 6px 20px rgba(13, 71, 161, 0.5)',
                  },
                }}
              >
                {isLoading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Iniciar Sesión'
                )}
              </Button>
            </form>

            {/* Footer */}
            <Box sx={{ mt: 4, pt: 3, borderTop: 1, borderColor: 'divider', textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                © 2025 Escuela Militar de Ingeniería
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                Vicerrectorado de Investigación y Posgrado
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default Login;
