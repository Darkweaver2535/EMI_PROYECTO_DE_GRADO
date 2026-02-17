/**
 * Componente ExportButton
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useState } from 'react';
import {
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
} from '@mui/material';
import {
  FileDownload as DownloadIcon,
  Image as ImageIcon,
  TableChart as ExcelIcon,
  PictureAsPdf as PdfIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { exportToPNG, exportDataToExcel, exportChartToPDF } from '../../utils';

export type ExportFormat = 'png' | 'excel' | 'pdf';

interface ExportButtonProps {
  elementId?: string;
  data?: Record<string, unknown>[];
  columns?: { key: string; header: string }[];
  filename?: string;
  title?: string;
  formats?: ExportFormat[];
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
  variant?: 'text' | 'outlined' | 'contained';
  onExport?: (format: ExportFormat) => void;
}

const ExportButton: React.FC<ExportButtonProps> = ({
  elementId,
  data,
  columns,
  filename = 'export',
  title = 'Reporte',
  formats = ['png', 'excel', 'pdf'],
  disabled = false,
  size = 'small',
  variant = 'outlined',
  onExport,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [loading, setLoading] = useState<ExportFormat | null>(null);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleExport = async (format: ExportFormat) => {
    handleClose();
    setLoading(format);

    try {
      switch (format) {
        case 'png':
          if (elementId) {
            await exportToPNG(elementId, filename);
          }
          break;
        case 'excel':
          if (data && columns) {
            exportDataToExcel(data, columns, filename);
          }
          break;
        case 'pdf':
          if (elementId) {
            await exportChartToPDF(elementId, filename, title);
          }
          break;
      }

      if (onExport) {
        onExport(format);
      }
    } catch (error) {
      console.error(`Error exporting to ${format}:`, error);
    } finally {
      setLoading(null);
    }
  };

  const formatOptions: Record<ExportFormat, { icon: React.ReactNode; label: string }> = {
    png: { icon: <ImageIcon fontSize="small" />, label: 'Imagen (PNG)' },
    excel: { icon: <ExcelIcon fontSize="small" />, label: 'Excel (XLSX)' },
    pdf: { icon: <PdfIcon fontSize="small" />, label: 'PDF' },
  };

  const isDisabled = (format: ExportFormat): boolean => {
    if (disabled) return true;
    if (loading) return true;
    
    switch (format) {
      case 'png':
      case 'pdf':
        return !elementId;
      case 'excel':
        return !data || !columns;
      default:
        return false;
    }
  };

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={handleClick}
        disabled={disabled || !!loading}
        startIcon={loading ? <CircularProgress size={16} /> : <DownloadIcon />}
        endIcon={<ExpandMoreIcon />}
      >
        Exportar
      </Button>
      
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        {formats.map(format => (
          <MenuItem
            key={format}
            onClick={() => handleExport(format)}
            disabled={isDisabled(format)}
          >
            <ListItemIcon>
              {loading === format ? (
                <CircularProgress size={20} />
              ) : (
                formatOptions[format].icon
              )}
            </ListItemIcon>
            <ListItemText primary={formatOptions[format].label} />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default ExportButton;
