/**
 * Componente ReportHistory
 * Muestra el historial de reportes generados
 * Sistema de Analítica OSINT - EMI Bolivia
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Button,
  Chip,
  TextField,
  InputAdornment,
  FormControl,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Tooltip,
  Paper,
  Skeleton
} from '@mui/material';
import {
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Email as EmailIcon,
  FilterList as FilterIcon,
  PictureAsPdf as PdfIcon,
  TableChart as ExcelIcon
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

import { ReportFile, ReportsHistoryResponse } from '../../types/reports.types';
import reportsService, { formatFileSize, getReportIcon, getReportTypeName } from '../../services/reportsService';

// Colores EMI
const EMI_GREEN = '#1B5E20';
const EMI_GOLD = '#FFD700';

interface ReportHistoryProps {
  onSendEmail?: (filename: string) => void;
}

const ReportHistory: React.FC<ReportHistoryProps> = ({ onSendEmail }) => {
  const [reports, setReports] = useState<ReportFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Paginación
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // Filtros
  const [typeFilter, setTypeFilter] = useState<'all' | 'pdf' | 'excel'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Estado para confirmación de eliminación
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; filename: string | null }>({
    open: false,
    filename: null
  });
  
  // Estado de descarga
  const [downloading, setDownloading] = useState<string | null>(null);

  // Cargar historial
  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await reportsService.getReportsHistory(
        typeFilter === 'all' ? undefined : typeFilter,
        30,
        100
      );
      
      if (response.success) {
        setReports(response.reports);
      } else {
        throw new Error(response.error || 'Error cargando historial');
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando historial');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [typeFilter]);

  // Filtrar reportes
  const filteredReports = reports.filter(report => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      report.filename.toLowerCase().includes(term) ||
      getReportTypeName(report.report_type).toLowerCase().includes(term)
    );
  });

  // Reportes paginados
  const paginatedReports = filteredReports.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  // Descargar reporte
  const handleDownload = async (filename: string) => {
    setDownloading(filename);
    try {
      await reportsService.downloadAndSaveReport(filename);
    } catch (error) {
      console.error('Error downloading:', error);
    } finally {
      setDownloading(null);
    }
  };

  // Eliminar reporte
  const handleDelete = async () => {
    if (!deleteDialog.filename) return;
    
    try {
      await reportsService.deleteReport(deleteDialog.filename);
      setReports(prev => prev.filter(r => r.filename !== deleteDialog.filename));
      setDeleteDialog({ open: false, filename: null });
    } catch (error) {
      console.error('Error deleting:', error);
    }
  };

  // Formatear fecha
  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), "dd/MM/yyyy HH:mm", { locale: es });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card elevation={2}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ color: EMI_GREEN, fontWeight: 600 }}>
            📂 Historial de Reportes
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              size="small"
              placeholder="Buscar..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                )
              }}
              sx={{ width: 200 }}
            />
            
            <FormControl size="small" sx={{ minWidth: 100 }}>
              <Select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as any)}
                displayEmpty
              >
                <MenuItem value="all">Todos</MenuItem>
                <MenuItem value="pdf">PDF</MenuItem>
                <MenuItem value="excel">Excel</MenuItem>
              </Select>
            </FormControl>
            
            <IconButton onClick={loadHistory} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: 'rgba(27, 94, 32, 0.08)' }}>
                <TableCell sx={{ fontWeight: 600 }}>Tipo</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Archivo</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Formato</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Tamaño</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Fecha</TableCell>
                <TableCell align="center" sx={{ fontWeight: 600 }}>Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                // Skeleton de carga
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton width={100} /></TableCell>
                    <TableCell><Skeleton width={200} /></TableCell>
                    <TableCell><Skeleton width={60} /></TableCell>
                    <TableCell><Skeleton width={60} /></TableCell>
                    <TableCell><Skeleton width={120} /></TableCell>
                    <TableCell><Skeleton width={100} /></TableCell>
                  </TableRow>
                ))
              ) : paginatedReports.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      {searchTerm ? 'No se encontraron reportes' : 'No hay reportes generados'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedReports.map((report) => (
                  <TableRow 
                    key={report.filename}
                    hover
                    sx={{ '&:hover': { bgcolor: 'rgba(27, 94, 32, 0.04)' } }}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography>{getReportIcon(report.report_type)}</Typography>
                        <Typography variant="body2">
                          {getReportTypeName(report.report_type)}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {report.filename}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={report.file_type === 'pdf' ? <PdfIcon /> : <ExcelIcon />}
                        label={report.file_type.toUpperCase()}
                        size="small"
                        color={report.file_type === 'pdf' ? 'error' : 'success'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{report.size_mb} MB</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{formatDate(report.created_at)}</Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                        <Tooltip title="Descargar">
                          <IconButton
                            size="small"
                            onClick={() => handleDownload(report.filename)}
                            disabled={downloading === report.filename}
                            sx={{ color: EMI_GREEN }}
                          >
                            <DownloadIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        
                        {onSendEmail && (
                          <Tooltip title="Enviar por email">
                            <IconButton
                              size="small"
                              onClick={() => onSendEmail(report.filename)}
                              color="primary"
                            >
                              <EmailIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        
                        <Tooltip title="Eliminar">
                          <IconButton
                            size="small"
                            onClick={() => setDeleteDialog({ open: true, filename: report.filename })}
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={filteredReports.length}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[5, 10, 25, 50]}
          labelRowsPerPage="Filas:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
        />
      </CardContent>

      {/* Diálogo de confirmación de eliminación */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, filename: null })}>
        <DialogTitle>Confirmar Eliminación</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Está seguro de que desea eliminar el reporte "{deleteDialog.filename}"?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Esta acción no se puede deshacer.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, filename: null })}>
            Cancelar
          </Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Eliminar
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default ReportHistory;
