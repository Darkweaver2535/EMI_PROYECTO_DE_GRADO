"""
SentimentAnalyzer - Wrapper Unificado
Sistema OSINT EMI

Este módulo es un WRAPPER delgado para mantener la compatibilidad
de la API con el módulo unificado de producción en la raíz.
Delega TODAS las llamadas al módulo `sentiment_analyzer.py` principal
para evitar duplicidad lógica e inconsistencias en la inferencia.
"""

import sys
import os
import logging
from typing import List, Dict, Any

# Asegurar que el módulo raíz esté en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sentiment_analyzer import (
    analizar_sentimiento,
    limpiar_texto,
    ejecutar_analisis_completo,
    fine_tune_model,
    evaluate_model,
    _batch_analyze
)

logger = logging.getLogger("OSINT.AI.SentimentWrapper")

class SentimentAnalyzer:
    """
    Analizador de sentimientos (Wrapper).
    
    Delega la clasificación, fine-tuning y evaluación al módulo
    raíz `sentiment_analyzer.py` (que usa Robertuito/BETO), manteniendo 
    la interfaz de clase exacta para retrocompatibilidad con el motor de IA.
    """
    
    LABEL_MAP = {
        0: "Negativo",
        1: "Neutral", 
        2: "Positivo"
    }
    
    def __init__(self, *args, **kwargs):
        """Inicializa el wrapper. Los argumentos se ignoran a favor de la config global."""
        self.logger = logger
        self.logger.info("Inicializando SentimentAnalyzer (Modo Wrapper Delgado)")
        
    def load_model(self, *args, **kwargs) -> bool:
        """
        Carga el modelo.
        El módulo raíz usa inicialización lazy (singleton), por lo que
        forzamos la carga enviando un texto vacío.
        """
        analizar_sentimiento("test carga")
        return True
        
    def fine_tune(self, training_data: List[Dict[str, Any]], *args, **kwargs) -> Dict[str, Any]:
        """
        Delega el fine-tuning al motor migrado en el módulo raíz.
        """
        self.logger.info("Delegando fine-tuning al módulo raíz...")
        return fine_tune_model(training_data, *args, **kwargs)
        
    def predict(self, text: str) -> Dict[str, Any]:
        """Predice el sentimiento de un texto individual."""
        res = analizar_sentimiento(text)
        
        # Mapeo a la estructura original de SentimentAnalyzer
        sentiment = res['sentimiento']
        if sentiment.lower() == 'negativo':
            sid = 0
        elif sentiment.lower() == 'neutral':
            sid = 1
        else:
            sid = 2
            
        return {
            "text": text[:200] + "..." if len(text) > 200 else text,
            "sentiment": sentiment,
            "sentiment_id": sid,
            "confidence": res['confianza'],
            "probabilities": {
                "Positivo": res['prob_positivo'],
                "Neutral": res['prob_neutral'],
                "Negativo": res['prob_negativo']
            }
        }
        
    def predict_batch(self, texts: List[str], return_probabilities: bool = False) -> List[Dict[str, Any]]:
        """Predicción en batch delegada a _batch_analyze() del módulo raíz."""
        batch_res = _batch_analyze(texts)
        results = []
        for text, res in zip(texts, batch_res):
            sentiment = res['sentimiento']
            if sentiment.lower() == 'negativo':
                sid = 0
            elif sentiment.lower() == 'neutral':
                sid = 1
            else:
                sid = 2
                
            mapped = {
                "text": text[:200] + "..." if len(text) > 200 else text,
                "sentiment": sentiment,
                "sentiment_id": sid,
                "confidence": res['confianza']
            }
            if return_probabilities:
                mapped["probabilities"] = {
                    "Positivo": res['prob_positivo'],
                    "Neutral": res['prob_neutral'],
                    "Negativo": res['prob_negativo']
                }
            results.append(mapped)
        return results
        
    def evaluate(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Delega la evaluación al módulo raíz."""
        return evaluate_model(test_data)
        
    def save_model(self, *args, **kwargs):
        """Manejo automático en fine_tune_model del módulo raíz."""
        pass 
        
    def get_model_info(self) -> Dict[str, Any]:
        """Obtiene información sobre la delegación activa."""
        return {
            "model_name": "Robertuito/BETO (via sentiment_analyzer.py)",
            "wrapper_mode": True,
            "status": "active"
        }
