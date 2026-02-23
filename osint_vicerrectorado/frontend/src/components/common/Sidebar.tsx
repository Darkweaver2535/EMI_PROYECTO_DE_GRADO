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
import { useAuth } from '../../contexts';
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
  TravelExplore as OSINTIcon,
  Psychology as NLPIcon,
  FactCheck as EvaluacionIcon,
  PeopleAlt as UsersIcon,
} from '@mui/icons-material';

const DRAWER_WIDTH = 260;

type UserRole = 'administrador' | 'vicerrector' | 'uebu';

interface MenuItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path?: string;
  children?: MenuItem[];
  /** Roles that can see this item. If empty/undefined, all roles can see it. */
  roles?: UserRole[];
}

const menuItems: MenuItem[] = [
  {
    id: 'osint',
    label: 'Inteligencia OSINT',
    icon: <OSINTIcon />,
    path: '/dashboard/osint',
    roles: ['administrador', 'vicerrector'],
  },
  {
    id: 'posts',
    label: 'Posts y Comentarios',
    icon: <PostsIcon />,
    path: '/dashboard/posts',
    roles: ['administrador', 'vicerrector'],
  },
  {
    id: 'dashboards',
    label: 'Analisis AI',
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
  {
    id: 'nlp',
    label: 'IA / ML / NLP',
    icon: <NLPIcon />,
    path: '/dashboard/nlp',
  },
  {
    id: 'evaluacion',
    label: 'Evaluacion Sistema',
    icon: <EvaluacionIcon />,
    path: '/dashboard/evaluacion',
    roles: ['administrador', 'vicerrector'],
  },
  {
    id: 'usuarios',
    label: 'Gestion Usuarios',
    icon: <UsersIcon />,
    path: '/dashboard/usuarios',
    roles: ['administrador'],
  },
];

const bottomMenuItems: MenuItem[] = [
  {
    id: 'settings',
    label: 'Configuracion',
    icon: <SettingsIcon />,
    path: '/dashboard/configuracion',
    roles: ['administrador', 'vicerrector'],
  },
  {
    id: 'help',
    label: 'Ayuda',
    icon: <HelpIcon />,
    path: '/dashboard/ayuda',
  },
];

interface SidebarProps {
  open: boolean;
  onClose?: () => void;
  variant?: 'permanent' | 'temporary';
}

/** Filter menu items based on user role */
const filterMenuByRole = (items: MenuItem[], role: UserRole): MenuItem[] => {
  return items
    .filter(item => !item.roles || item.roles.includes(role))
    .map(item => {
      if (item.children) {
        const filteredChildren = filterMenuByRole(item.children, role);
        if (filteredChildren.length === 0) return null;
        return { ...item, children: filteredChildren };
      }
      return item;
    })
    .filter(Boolean) as MenuItem[];
};

const Sidebar: React.FC<SidebarProps> = ({
  open,
  onClose,
  variant = 'permanent',
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const { user } = useAuth();
  
  const userRole: UserRole = (user?.rol as UserRole) || 'uebu';
  const visibleMenuItems = React.useMemo(() => filterMenuByRole(menuItems, userRole), [userRole]);
  const visibleBottomItems = React.useMemo(() => filterMenuByRole(bottomMenuItems, userRole), [userRole]);
  
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
          {visibleMenuItems.map(item => renderMenuItem(item))}
        </List>
        
        <Divider sx={{ my: 2 }} />
        
        <List>
          {visibleBottomItems.map(item => renderMenuItem(item))}
        </List>
      </Box>
      
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" display="block" textAlign="center">
          SADUTO v1.0
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" textAlign="center">
          © 2025 EMI Bolivia
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
