/**
 * Utilidades para exportación de datos
 * Sistema OSINT EMI - Sprint 4
 */

import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';
import { ExportFormat } from '../types';

interface ExportToImageOptions {
  element: HTMLElement;
  filename: string;
  backgroundColor?: string;
}

interface ExportToExcelOptions {
  data: Record<string, unknown>[];
  filename: string;
  sheetName?: string;
  headers?: string[];
}

interface ExportToPDFOptions {
  title: string;
  filename: string;
  content: {
    type: 'text' | 'table' | 'image';
    data: string | Record<string, unknown>[] | HTMLElement;
    headers?: string[];
  }[];
  orientation?: 'portrait' | 'landscape';
  includeTimestamp?: boolean;
}

export const exportToImage = async ({
  element,
  filename,
  backgroundColor = '#ffffff',
}: ExportToImageOptions): Promise<void> => {
  try {
    const canvas = await html2canvas(element, {
      backgroundColor,
      scale: 2,
      useCORS: true,
      logging: false,
    });

    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (error) {
    console.error('Error exporting to image:', error);
    throw new Error('No se pudo exportar la imagen');
  }
};

export const exportToExcel = ({
  data,
  filename,
  sheetName = 'Datos',
  headers,
}: ExportToExcelOptions): void => {
  try {
    const worksheet = XLSX.utils.json_to_sheet(data, {
      header: headers,
    });

    // Auto-ajustar ancho de columnas
    const maxWidths: number[] = [];
    data.forEach((row) => {
      Object.values(row).forEach((value, index) => {
        const length = String(value).length;
        maxWidths[index] = Math.max(maxWidths[index] || 10, length);
      });
    });

    worksheet['!cols'] = maxWidths.map((w) => ({ wch: Math.min(w + 2, 50) }));

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

    XLSX.writeFile(workbook, `${filename}.xlsx`);
  } catch (error) {
    console.error('Error exporting to Excel:', error);
    throw new Error('No se pudo exportar a Excel');
  }
};

export const exportToPDF = async ({
  title,
  filename,
  content,
  orientation = 'portrait',
  includeTimestamp = true,
}: ExportToPDFOptions): Promise<void> => {
  try {
    const pdf = new jsPDF({
      orientation,
      unit: 'mm',
      format: 'a4',
    });

    const pageWidth = pdf.internal.pageSize.getWidth();
    let yPosition = 20;

    // Header con logo EMI (placeholder)
    pdf.setFillColor(25, 118, 210);
    pdf.rect(0, 0, pageWidth, 15, 'F');
    pdf.setTextColor(255, 255, 255);
    pdf.setFontSize(12);
    pdf.text('Sistema OSINT - EMI Bolivia', 10, 10);

    // Título
    yPosition = 25;
    pdf.setTextColor(0, 0, 0);
    pdf.setFontSize(18);
    pdf.text(title, pageWidth / 2, yPosition, { align: 'center' });
    yPosition += 10;

    // Timestamp
    if (includeTimestamp) {
      pdf.setFontSize(10);
      pdf.setTextColor(100, 100, 100);
      pdf.text(
        `Generado: ${new Date().toLocaleString('es-BO')}`,
        pageWidth / 2,
        yPosition,
        { align: 'center' }
      );
      yPosition += 10;
    }

    // Contenido
    for (const item of content) {
      if (yPosition > pdf.internal.pageSize.getHeight() - 30) {
        pdf.addPage();
        yPosition = 20;
      }

      switch (item.type) {
        case 'text':
          pdf.setFontSize(11);
          pdf.setTextColor(0, 0, 0);
          const lines = pdf.splitTextToSize(
            String(item.data),
            pageWidth - 20
          );
          pdf.text(lines, 10, yPosition);
          yPosition += lines.length * 6 + 5;
          break;

        case 'table':
          if (Array.isArray(item.data) && item.data.length > 0) {
            const tableData = item.data as Record<string, unknown>[];
            const headers = item.headers || Object.keys(tableData[0]);
            const rows = tableData.map((row) =>
              headers.map((h) => String(row[h] ?? ''))
            );

            autoTable(pdf, {
              head: [headers],
              body: rows,
              startY: yPosition,
              styles: { fontSize: 9 },
              headStyles: { fillColor: [25, 118, 210] },
              alternateRowStyles: { fillColor: [245, 245, 245] },
            });

            yPosition = (pdf as jsPDF & { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 10;
          }
          break;

        case 'image':
          if (item.data instanceof HTMLElement) {
            const canvas = await html2canvas(item.data, {
              backgroundColor: '#ffffff',
              scale: 2,
            });
            const imgData = canvas.toDataURL('image/png');
            const imgWidth = pageWidth - 20;
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            if (yPosition + imgHeight > pdf.internal.pageSize.getHeight() - 10) {
              pdf.addPage();
              yPosition = 20;
            }

            pdf.addImage(imgData, 'PNG', 10, yPosition, imgWidth, imgHeight);
            yPosition += imgHeight + 10;
          }
          break;
      }
    }

    // Footer
    const totalPages = pdf.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      pdf.setFontSize(8);
      pdf.setTextColor(150, 150, 150);
      pdf.text(
        `Página ${i} de ${totalPages}`,
        pageWidth / 2,
        pdf.internal.pageSize.getHeight() - 5,
        { align: 'center' }
      );
    }

    pdf.save(`${filename}.pdf`);
  } catch (error) {
    console.error('Error exporting to PDF:', error);
    throw new Error('No se pudo exportar a PDF');
  }
};

export const downloadJSON = (
  data: unknown,
  filename: string
): void => {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.json`;
  link.click();
  URL.revokeObjectURL(url);
};

export const handleExport = async (
  format: ExportFormat,
  options: {
    element?: HTMLElement;
    data?: Record<string, unknown>[];
    title: string;
    filename: string;
  }
): Promise<void> => {
  const { element, data, title, filename } = options;

  switch (format) {
    case 'png':
      if (element) {
        await exportToImage({ element, filename });
      }
      break;

    case 'excel':
      if (data) {
        exportToExcel({ data, filename, sheetName: title });
      }
      break;

    case 'pdf':
      const content: ExportToPDFOptions['content'] = [];
      
      if (element) {
        content.push({ type: 'image', data: element });
      }
      
      if (data) {
        content.push({ type: 'table', data });
      }

      await exportToPDF({
        title,
        filename,
        content,
      });
      break;
  }
};

// Alias for backward compatibility
export const exportToPNG = async (elementId: string, filename?: string, title?: string): Promise<void> => {
  const element = document.getElementById(elementId);
  if (!element) {
    throw new Error(`Element with id "${elementId}" not found`);
  }
  await exportToImage({
    element,
    filename: filename || `export-${Date.now()}`,
  });
};

// Wrapper para exportToExcel con firma simplificada
export const exportDataToExcel = (
  data: Record<string, unknown>[],
  columns: { key: string; header: string }[],
  filename: string
): void => {
  const headers = columns.map(col => col.header);
  const formattedData = data.map(row => {
    const newRow: Record<string, unknown> = {};
    columns.forEach(col => {
      newRow[col.header] = row[col.key];
    });
    return newRow;
  });
  
  exportToExcel({
    data: formattedData,
    filename,
    headers
  });
};

// Wrapper para exportToPDF con firma simplificada
export const exportChartToPDF = async (
  elementId: string,
  filename: string,
  title: string
): Promise<void> => {
  const element = document.getElementById(elementId);
  if (!element) {
    throw new Error(`Element with id "${elementId}" not found`);
  }
  
  await exportToPDF({
    title,
    filename,
    content: [{ type: 'image', data: element }],
  });
};
