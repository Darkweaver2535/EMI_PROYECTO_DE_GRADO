/**
 * Componente Sidebar
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Box,
  Typography,
  Collapse,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  SentimentSatisfied as SentimentIcon,
  Stars as ReputationIcon,
  Warning as AlertsIcon,
  BarChart as BenchmarkingIcon,
  Settings as SettingsIcon,
  Help as HelpIcon,
  ExpandLess,
  ExpandMore,
  Forum as PostsIcon,
} from '@mui/icons-material';

const DRAWER_WIDTH = 260;

interface MenuItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path?: string;
  children?: MenuItem[];
}

const menuItems: MenuItem[] = [
  {
    id: 'posts',
    label: '📝 Posts y Comentarios',
    icon: <PostsIcon />,
    path: '/dashboard/posts',
  },
  {
    id: 'dashboards',
    label: 'Análisis AI',
    icon: <DashboardIcon />,
    children: [
      {
        id: 'sentiment',
        label: 'Análisis de Sentimientos',
        icon: <SentimentIcon />,
        path: '/dashboard/sentiment',
      },
      {
        id: 'reputation',
        label: 'Reputación',
        icon: <ReputationIcon />,
        path: '/dashboard/reputation',
      },
      {
        id: 'alerts',
        label: 'Alertas y Anomalías',
        icon: <AlertsIcon />,
        path: '/dashboard/alerts',
      },
      {
        id: 'benchmarking',
        label: 'Benchmarking',
        icon: <BenchmarkingIcon />,
        path: '/dashboard/benchmarking',
      },
    ],
  },
];

const bottomMenuItems: MenuItem[] = [
  {
    id: 'settings',
    label: 'Configuración',
    icon: <SettingsIcon />,
    path: '/settings',
  },
  {
    id: 'help',
    label: 'Ayuda',
    icon: <HelpIcon />,
    path: '/help',
  },
];

interface SidebarProps {
  open: boolean;
  onClose?: () => void;
  variant?: 'permanent' | 'temporary';
}

const Sidebar: React.FC<SidebarProps> = ({
  open,
  onClose,
  variant = 'permanent',
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  
  const [expandedItems, setExpandedItems] = React.useState<string[]>(['dashboards']);

  const handleToggle = (itemId: string) => {
    setExpandedItems(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    if (variant === 'temporary' && onClose) {
      onClose();
    }
  };

  const isActive = (path?: string): boolean => {
    if (!path) return false;
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const renderMenuItem = (item: MenuItem, depth = 0) => {
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.includes(item.id);
    const active = isActive(item.path);

    return (
      <React.Fragment key={item.id}>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => {
              if (hasChildren) {
                handleToggle(item.id);
              } else if (item.path) {
                handleNavigate(item.path);
              }
            }}
            selected={active}
            sx={{
              pl: 2 + depth * 2,
              borderRadius: 1,
              mx: 1,
              my: 0.5,
              '&.Mui-selected': {
                backgroundColor: theme.palette.primary.main + '20',
                '&:hover': {
                  backgroundColor: theme.palette.primary.main + '30',
                },
              },
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 40,
                color: active ? theme.palette.primary.main : 'inherit',
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{
                fontSize: depth > 0 ? '0.875rem' : '0.9rem',
                fontWeight: active ? 600 : 400,
                color: active ? theme.palette.primary.main : 'inherit',
              }}
            />
            {hasChildren && (isExpanded ? <ExpandLess /> : <ExpandMore />)}
          </ListItemButton>
        </ListItem>
        
        {hasChildren && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {item.children!.map(child => renderMenuItem(child, depth + 1))}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  const drawerContent = (
    <>
      <Toolbar />
      <Box sx={{ overflow: 'auto', flex: 1 }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
            NAVEGACIÓN
          </Typography>
        </Box>
        <List>
          {menuItems.map(item => renderMenuItem(item))}
        </List>
        
        <Divider sx={{ my: 2 }} />
        
        <List>
          {bottomMenuItems.map(item => renderMenuItem(item))}
        </List>
      </Box>
      
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" display="block" textAlign="center">
          Sistema OSINT v1.0
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" textAlign="center">
          © 2024 EMI Bolivia
        </Typography>
      </Box>
    </>
  );

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          borderRight: `1px solid ${theme.palette.divider}`,
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
};

export { DRAWER_WIDTH };
export default Sidebar;
