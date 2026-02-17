/**
 * Página 404 - No Encontrado
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Button, Container } from '@mui/material';
import { Home as HomeIcon, ArrowBack as BackIcon } from '@mui/icons-material';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          textAlign: 'center',
          py: 4,
        }}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: { xs: '6rem', md: '10rem' },
            fontWeight: 700,
            color: 'primary.main',
            lineHeight: 1,
          }}
        >
          404
        </Typography>
        
        <Typography
          variant="h4"
          component="h1"
          gutterBottom
          sx={{ mt: 2 }}
        >
          Página no encontrada
        </Typography>
        
        <Typography
          variant="body1"
          color="text.secondary"
          sx={{ mb: 4, maxWidth: 400 }}
        >
          Lo sentimos, la página que buscas no existe o ha sido movida.
          Verifica la URL o regresa a la página principal.
        </Typography>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<BackIcon />}
            onClick={() => navigate(-1)}
          >
            Volver atrás
          </Button>
          <Button
            variant="contained"
            startIcon={<HomeIcon />}
            onClick={() => navigate('/dashboard/sentiment')}
          >
            Ir al inicio
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default NotFound;
