/**
 * Componente KPICard
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Skeleton,
  useTheme,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
} from '@mui/icons-material';

export type TrendDirection = 'up' | 'down' | 'stable';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: TrendDirection;
  trendValue?: string;
  icon?: React.ReactNode;
  color?: 'primary' | 'success' | 'warning' | 'error' | 'info';
  loading?: boolean;
  onClick?: () => void;
}

const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  icon,
  color = 'primary',
  loading = false,
  onClick,
}) => {
  const theme = useTheme();

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon />;
      case 'down':
        return <TrendingDownIcon />;
      default:
        return <TrendingFlatIcon />;
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return theme.palette.success.main;
      case 'down':
        return theme.palette.error.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getColorValue = () => {
    switch (color) {
      case 'success':
        return theme.palette.success.main;
      case 'warning':
        return theme.palette.warning.main;
      case 'error':
        return theme.palette.error.main;
      case 'info':
        return theme.palette.info.main;
      default:
        return theme.palette.primary.main;
    }
  };

  if (loading) {
    return (
      <Card
        sx={{
          height: '100%',
          minHeight: 140,
        }}
      >
        <CardContent>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={48} sx={{ mt: 1 }} />
          <Skeleton variant="text" width="80%" height={20} sx={{ mt: 1 }} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        height: '100%',
        minHeight: 140,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease-in-out',
        '&:hover': onClick
          ? {
              transform: 'translateY(-2px)',
              boxShadow: theme.shadows[4],
            }
          : {},
        borderTop: `4px solid ${getColorValue()}`,
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              fontSize: '0.75rem',
            }}
          >
            {title}
          </Typography>
          {icon && (
            <Box
              sx={{
                color: getColorValue(),
                opacity: 0.8,
              }}
            >
              {icon}
            </Box>
          )}
        </Box>

        <Typography
          variant="h4"
          component="div"
          sx={{
            fontWeight: 700,
            mt: 1,
            color: getColorValue(),
          }}
        >
          {value}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, gap: 0.5 }}>
          {trend && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                color: getTrendColor(),
              }}
            >
              {getTrendIcon()}
              {trendValue && (
                <Typography variant="body2" sx={{ ml: 0.5, fontWeight: 500 }}>
                  {trendValue}
                </Typography>
              )}
            </Box>
          )}
          {subtitle && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ ml: trend ? 1 : 0 }}
            >
              {subtitle}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default KPICard;
