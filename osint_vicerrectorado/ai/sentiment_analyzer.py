"""
SentimentAnalyzer - Análisis de Sentimientos con BETO
Sistema de Analítica EMI - Sprint 3

Este módulo implementa análisis de sentimientos utilizando BETO
(BERT pre-entrenado en español) con capacidad de fine-tuning.

Características:
- Fine-tuning con datos anotados manualmente
- Clasificación en 3 categorías: Positivo, Negativo, Neutral
- Predicción batch eficiente
- Evaluación con métricas estándar (accuracy, F1, precision, recall)
- Persistencia de modelos entrenados

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import os
import json
import logging
import pickle
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report
)


class SentimentDataset(Dataset):
    """
    Dataset personalizado para entrenamiento de sentimientos.
    
    Args:
        texts: Lista de textos a clasificar
        labels: Lista de etiquetas (0=Negativo, 1=Neutral, 2=Positivo)
        tokenizer: Tokenizer de BETO/BERT
        max_length: Longitud máxima de secuencia
    """
    
    def __init__(
        self,
        texts: List[str],
        labels: List[int],
        tokenizer,
        max_length: int = 512
    ):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self) -> int:
        return len(self.texts)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


class SentimentAnalyzer:
    """
    Analizador de sentimientos basado en BETO (BERT español).
    
    Implementa análisis de sentimientos con capacidad de:
    - Cargar modelo pre-entrenado BETO
    - Fine-tuning con datos específicos del dominio
    - Predicción individual y batch
    - Evaluación de rendimiento
    - Persistencia de modelos
    
    Attributes:
        model_name (str): Nombre del modelo base de Hugging Face
        model: Modelo de clasificación de secuencias
        tokenizer: Tokenizer para procesamiento de texto
        device: Dispositivo de cómputo (CPU/GPU)
        labels (List[str]): Etiquetas de clasificación
        
    Example:
        >>> analyzer = SentimentAnalyzer()
        >>> analyzer.load_model()
        >>> result = analyzer.predict("La EMI es excelente!")
        >>> print(result)
        {'sentiment': 'Positivo', 'confidence': 0.95, 'probabilities': {...}}
    """
    
    # Mapeo de etiquetas
    LABEL_MAP = {
        0: "Negativo",
        1: "Neutral", 
        2: "Positivo"
    }
    
    LABEL_TO_ID = {
        "Negativo": 0, "negativo": 0,
        "Neutral": 1, "neutral": 1,
        "Positivo": 2, "positivo": 2
    }
    
    def __init__(
        self,
        model_name: str = "dccuchile/bert-base-spanish-wwm-uncased",
        models_dir: str = None,
        device: str = None,
        max_length: int = 512,
        batch_size: int = 16
    ):
        """
        Inicializa el analizador de sentimientos.
        
        Args:
            model_name: Nombre del modelo base de Hugging Face
            models_dir: Directorio para guardar/cargar modelos
            device: Dispositivo ('cuda', 'cpu', 'mps' o None para auto)
            max_length: Longitud máxima de tokens
            batch_size: Tamaño de batch para predicción
        """
        self.logger = logging.getLogger("OSINT.AI.Sentiment")
        
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        
        # Configurar directorio de modelos
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            self.models_dir = Path(__file__).parent / "models" / "beto_finetuned"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Detectar dispositivo
        if device:
            self.device = torch.device(device)
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        
        self.logger.info(f"Dispositivo seleccionado: {self.device}")
        
        self.model = None
        self.tokenizer = None
        self.is_trained = False
        self.training_metrics = {}
    
    def load_model(self, model_path: str = None) -> bool:
        """
        Carga el modelo BETO desde Hugging Face o desde ruta local.
        
        Si existe un modelo fine-tuned guardado, lo carga. De lo contrario,
        carga el modelo base pre-entrenado.
        
        Args:
            model_path: Ruta opcional a modelo guardado
            
        Returns:
            True si la carga fue exitosa
            
        Raises:
            RuntimeError: Si hay error al cargar el modelo
        """
        try:
            # Verificar si hay modelo fine-tuned guardado
            if model_path:
                load_path = Path(model_path)
            else:
                load_path = self.models_dir
            
            config_file = load_path / "config.json"
            
            if config_file.exists():
                self.logger.info(f"Cargando modelo fine-tuned desde {load_path}")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(load_path),
                    num_labels=3,
                    local_files_only=True
                )
                self.tokenizer = AutoTokenizer.from_pretrained(
                    str(load_path),
                    local_files_only=True
                )
                self.is_trained = True
            else:
                self.logger.info(f"Cargando modelo base: {self.model_name}")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=3,
                    id2label=self.LABEL_MAP,
                    label2id={v: k for k, v in self.LABEL_MAP.items()}
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.is_trained = False
            
            self.model.to(self.device)
            self.model.eval()
            
            self.logger.info("Modelo cargado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al cargar modelo: {str(e)}")
            raise RuntimeError(f"No se pudo cargar el modelo: {str(e)}")
    
    def fine_tune(
        self,
        training_data: List[Dict[str, Any]],
        validation_split: float = 0.2,
        epochs: int = 3,
        learning_rate: float = 2e-5,
        warmup_steps: int = 500,
        weight_decay: float = 0.01,
        early_stopping_patience: int = 3,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        Fine-tuning del modelo con datos anotados.
        
        Args:
            training_data: Lista de dicts con 'text' y 'label'
            validation_split: Proporción para validación (0-1)
            epochs: Número de épocas de entrenamiento
            learning_rate: Tasa de aprendizaje
            warmup_steps: Pasos de warmup
            weight_decay: Regularización L2
            early_stopping_patience: Épocas sin mejora antes de parar
            save_model: Si guardar el modelo después del entrenamiento
            
        Returns:
            Dict con métricas de entrenamiento
            
        Example:
            >>> data = [
            ...     {"text": "Excelente servicio", "label": "Positivo"},
            ...     {"text": "Muy malo", "label": "Negativo"}
            ... ]
            >>> metrics = analyzer.fine_tune(data)
        """
        if self.model is None or self.tokenizer is None:
            self.load_model()
        
        self.logger.info(f"Iniciando fine-tuning con {len(training_data)} ejemplos")
        
        # Preparar datos
        texts = [item['text'] for item in training_data]
        labels = [
            self.LABEL_TO_ID.get(item['label'], 1) 
            for item in training_data
        ]
        
        # Split train/validation
        n_samples = len(texts)
        n_val = int(n_samples * validation_split)
        indices = np.random.permutation(n_samples)
        
        train_texts = [texts[i] for i in indices[n_val:]]
        train_labels = [labels[i] for i in indices[n_val:]]
        val_texts = [texts[i] for i in indices[:n_val]]
        val_labels = [labels[i] for i in indices[:n_val]]
        
        self.logger.info(f"Train: {len(train_texts)}, Validation: {len(val_texts)}")
        
        # Crear datasets
        train_dataset = SentimentDataset(
            train_texts, train_labels, self.tokenizer, self.max_length
        )
        val_dataset = SentimentDataset(
            val_texts, val_labels, self.tokenizer, self.max_length
        )
        
        # Configurar entrenamiento
        training_args = TrainingArguments(
            output_dir=str(self.models_dir / "checkpoints"),
            num_train_epochs=epochs,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            warmup_steps=warmup_steps,
            weight_decay=weight_decay,
            learning_rate=learning_rate,
            logging_dir=str(self.models_dir / "logs"),
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            greater_is_better=True,
            save_total_limit=2,
            report_to=[]  # Desactivar wandb/tensorboard
        )
        
        # Función de métricas
        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            predictions = np.argmax(logits, axis=-1)
            accuracy = accuracy_score(labels, predictions)
            precision, recall, f1, _ = precision_recall_fscore_support(
                labels, predictions, average='weighted'
            )
            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1
            }
        
        # Crear trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
            callbacks=[
                EarlyStoppingCallback(
                    early_stopping_patience=early_stopping_patience
                )
            ]
        )
        
        # Entrenar
        self.logger.info("Iniciando entrenamiento...")
        train_result = trainer.train()
        
        # Evaluar
        eval_result = trainer.evaluate()
        
        # Guardar métricas
        self.training_metrics = {
            "train_loss": train_result.training_loss,
            "train_runtime": train_result.metrics.get("train_runtime", 0),
            "train_samples_per_second": train_result.metrics.get(
                "train_samples_per_second", 0
            ),
            "eval_accuracy": eval_result.get("eval_accuracy", 0),
            "eval_f1": eval_result.get("eval_f1", 0),
            "eval_precision": eval_result.get("eval_precision", 0),
            "eval_recall": eval_result.get("eval_recall", 0),
            "total_samples": len(training_data),
            "train_samples": len(train_texts),
            "val_samples": len(val_texts),
            "epochs": epochs,
            "timestamp": datetime.now().isoformat()
        }
        
        self.is_trained = True
        
        # Guardar modelo
        if save_model:
            self.save_model()
        
        self.logger.info(
            f"Fine-tuning completado. Accuracy: {self.training_metrics['eval_accuracy']:.4f}"
        )
        
        return self.training_metrics
    
    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predice el sentimiento de un texto individual.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Dict con sentimiento predicho, confianza y probabilidades
            
        Example:
            >>> result = analyzer.predict("La EMI es una gran universidad")
            >>> print(result['sentiment'])  # 'Positivo'
            >>> print(result['confidence'])  # 0.92
        """
        if self.model is None:
            raise RuntimeError("Modelo no cargado. Ejecute load_model() primero.")
        
        # Tokenizar
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding='max_length',
            return_tensors='pt'
        )
        
        # Mover a dispositivo
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Predecir
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
        
        # Obtener predicción
        probs = probabilities[0].cpu().numpy()
        predicted_label = int(np.argmax(probs))
        confidence = float(probs[predicted_label])
        
        return {
            "text": text[:200] + "..." if len(text) > 200 else text,
            "sentiment": self.LABEL_MAP[predicted_label],
            "sentiment_id": predicted_label,
            "confidence": confidence,
            "probabilities": {
                self.LABEL_MAP[i]: float(probs[i]) 
                for i in range(3)
            }
        }
    
    def predict_batch(
        self,
        texts: List[str],
        return_probabilities: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Predicción eficiente en batch de múltiples textos.
        
        Args:
            texts: Lista de textos a analizar
            return_probabilities: Si incluir probabilidades completas
            
        Returns:
            Lista de resultados de predicción
            
        Note:
            Optimizado para procesamiento eficiente de grandes volúmenes.
            Target: <30 segundos para 100 textos.
        """
        if self.model is None:
            raise RuntimeError("Modelo no cargado. Ejecute load_model() primero.")
        
        if not texts:
            return []
        
        self.logger.info(f"Procesando batch de {len(texts)} textos")
        
        results = []
        self.model.eval()
        
        # Procesar en batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            
            # Tokenizar batch
            inputs = self.tokenizer(
                batch_texts,
                truncation=True,
                max_length=self.max_length,
                padding=True,
                return_tensors='pt'
            )
            
            # Mover a dispositivo
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predecir
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
            
            # Procesar resultados
            probs = probabilities.cpu().numpy()
            
            for j, text in enumerate(batch_texts):
                predicted_label = int(np.argmax(probs[j]))
                confidence = float(probs[j][predicted_label])
                
                result = {
                    "text": text[:200] + "..." if len(text) > 200 else text,
                    "sentiment": self.LABEL_MAP[predicted_label],
                    "sentiment_id": predicted_label,
                    "confidence": confidence
                }
                
                if return_probabilities:
                    result["probabilities"] = {
                        self.LABEL_MAP[k]: float(probs[j][k])
                        for k in range(3)
                    }
                
                results.append(result)
        
        self.logger.info(f"Batch completado. {len(results)} predicciones.")
        return results
    
    def evaluate(
        self,
        test_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evalúa el modelo con datos de prueba.
        
        Args:
            test_data: Lista de dicts con 'text' y 'label'
            
        Returns:
            Dict con métricas de evaluación completas
        """
        if self.model is None:
            raise RuntimeError("Modelo no cargado. Ejecute load_model() primero.")
        
        self.logger.info(f"Evaluando modelo con {len(test_data)} ejemplos")
        
        texts = [item['text'] for item in test_data]
        true_labels = [
            self.LABEL_TO_ID.get(item['label'], 1) 
            for item in test_data
        ]
        
        # Obtener predicciones
        predictions = self.predict_batch(texts)
        pred_labels = [p['sentiment_id'] for p in predictions]
        
        # Calcular métricas
        accuracy = accuracy_score(true_labels, pred_labels)
        precision, recall, f1, support = precision_recall_fscore_support(
            true_labels, pred_labels, average=None, labels=[0, 1, 2]
        )
        
        precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
            true_labels, pred_labels, average='weighted'
        )
        
        conf_matrix = confusion_matrix(true_labels, pred_labels, labels=[0, 1, 2])
        
        # Reporte detallado
        report = classification_report(
            true_labels, pred_labels,
            target_names=["Negativo", "Neutral", "Positivo"],
            output_dict=True
        )
        
        evaluation_metrics = {
            "accuracy": float(accuracy),
            "precision_weighted": float(precision_weighted),
            "recall_weighted": float(recall_weighted),
            "f1_weighted": float(f1_weighted),
            "per_class": {
                self.LABEL_MAP[i]: {
                    "precision": float(precision[i]),
                    "recall": float(recall[i]),
                    "f1": float(f1[i]),
                    "support": int(support[i])
                }
                for i in range(3)
            },
            "confusion_matrix": conf_matrix.tolist(),
            "classification_report": report,
            "total_samples": len(test_data),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"Evaluación completada. Accuracy: {accuracy:.4f}")
        
        return evaluation_metrics
    
    def save_model(self, path: str = None) -> str:
        """
        Guarda el modelo fine-tuned y tokenizer.
        
        Args:
            path: Ruta donde guardar (opcional)
            
        Returns:
            Ruta donde se guardó el modelo
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("No hay modelo para guardar")
        
        save_path = Path(path) if path else self.models_dir
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Guardar modelo y tokenizer
        self.model.save_pretrained(str(save_path))
        self.tokenizer.save_pretrained(str(save_path))
        
        # Guardar métricas de entrenamiento
        metrics_path = save_path / "training_metrics.json"
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(self.training_metrics, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Modelo guardado en: {save_path}")
        return str(save_path)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información del modelo actual.
        
        Returns:
            Dict con información del modelo
        """
        info = {
            "model_name": self.model_name,
            "device": str(self.device),
            "is_trained": self.is_trained,
            "max_length": self.max_length,
            "batch_size": self.batch_size,
            "labels": list(self.LABEL_MAP.values()),
            "models_dir": str(self.models_dir),
            "model_loaded": self.model is not None
        }
        
        if self.training_metrics:
            info["training_metrics"] = self.training_metrics
        
        if self.model is not None:
            info["model_parameters"] = sum(
                p.numel() for p in self.model.parameters()
            )
        
        return info


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Crear analizador
    analyzer = SentimentAnalyzer()
    
    # Cargar modelo
    print("Cargando modelo BETO...")
    analyzer.load_model()
    
    # Ejemplo de predicción
    test_texts = [
        "La EMI es una excelente universidad, muy recomendada!",
        "El servicio de atención es pésimo, nadie responde",
        "La biblioteca está abierta de 8 a 20 horas",
        "Me encanta estudiar aquí, los profesores son muy buenos",
        "Las instalaciones están en mal estado, necesitan reparación"
    ]
    
    print("\n--- Predicciones ---")
    for text in test_texts:
        result = analyzer.predict(text)
        print(f"\nTexto: {text}")
        print(f"Sentimiento: {result['sentiment']} ({result['confidence']:.2%})")
    
    # Info del modelo
    print("\n--- Info del Modelo ---")
    print(json.dumps(analyzer.get_model_info(), indent=2))
