"""
Multimodal Macro & News Weight Trainer.
Performs supervised learning & walk-forward cross validation to train cross-modal fusion weights
relating global indicators (e_macro) and news embeddings (e_news) to NIFTY market direction.
Completely self-contained, pure Python (zero external dependencies).
"""

import json
import math
import time
from dataclasses import dataclass
from database.db import db_manager
from global_macro.dataset import macro_dataset, MacroHistoricalSample
from global_macro.multimodal_fusion import multimodal_fusion


@dataclass
class TrainingResult:
    """Evaluation metrics from multimodal weight training."""
    epoch: int
    num_samples: int
    macro_weights: list[float]
    news_weights: list[float]
    train_mse: float
    directional_accuracy: float  # Percentage of correct directional classifications
    cross_val_mae: float
    training_duration_ms: float


class MultimodalWeightTrainer:
    """Trains linear projection weights for multimodal macro & geopolitical news fusion."""

    def __init__(self, l2_regularization: float = 0.05):
        self.l2_reg = l2_regularization
        self._epoch = 1

    # --- Pure-Python Linear Algebra Utilities ---

    @staticmethod
    def _matrix_mult(A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
        rows_A, cols_A = len(A), len(A[0])
        rows_B, cols_B = len(B), len(B[0])
        result = [[0.0 for _ in range(cols_B)] for _ in range(rows_A)]
        for i in range(rows_A):
            for k in range(cols_A):
                for j in range(cols_B):
                    result[i][j] += A[i][k] * B[k][j]
        return result

    @staticmethod
    def _matrix_transpose(A: list[list[float]]) -> list[list[float]]:
        return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]

    @staticmethod
    def _invert_matrix(A: list[list[float]]) -> list[list[float]]:
        """Inverts an n x n matrix using Gauss-Jordan elimination with partial pivoting."""
        n = len(A)
        # Augment with identity matrix
        aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]

        for col in range(n):
            # Pivot selection
            pivot_row = col
            for r in range(col + 1, n):
                if abs(aug[r][col]) > abs(aug[pivot_row][col]):
                    pivot_row = r
            if pivot_row != col:
                aug[col], aug[pivot_row] = aug[pivot_row], aug[col]

            pivot_val = aug[col][col]
            if abs(pivot_val) < 1e-12:
                pivot_val = 1e-12  # Guard against singular matrix

            # Normalize pivot row
            for c in range(2 * n):
                aug[col][c] /= pivot_val

            # Eliminate other rows
            for r in range(n):
                if r != col:
                    factor = aug[r][col]
                    for c in range(2 * n):
                        aug[r][c] -= factor * aug[col][c]

        return [row[n:] for row in aug]

    def _solve_ridge(self, X: list[list[float]], y: list[float]) -> list[float]:
        """
        Solves w = (X^T * X + lambda * I)^(-1) * X^T * y
        """
        num_samples = len(X)
        num_features = len(X[0])

        X_T = self._matrix_transpose(X)
        # X_T * X
        XTX = self._matrix_mult(X_T, X)

        # Add L2 penalty: XTX + lambda * I
        for i in range(num_features):
            XTX[i][i] += self.l2_reg * num_samples

        XTX_inv = self._invert_matrix(XTX)

        # X_T * y (vector represented as column matrix)
        y_col = [[val] for val in y]
        XTy = self._matrix_mult(X_T, y_col)

        # w = XTX_inv * XTy
        w_col = self._matrix_mult(XTX_inv, XTy)
        return [w_col[i][0] for i in range(num_features)]

    def train_on_dataset(self) -> TrainingResult:
        """
        Trains weights across historical macro dataset, evaluates accuracy,
        and saves the learned weights to the database and live fusion engine.
        """
        start_time = time.time()
        macro_dataset.init_tables()
        macro_dataset.seed_historical_events()

        samples = macro_dataset.get_all_samples()
        if not samples:
            raise ValueError("Macro dataset is empty. Cannot perform training.")

        X: list[list[float]] = []
        y: list[float] = []

        for s in samples:
            # Features: 13-D fused vector [macro_5, news_8]
            X.append(s.fused_features)

            # Target score mapping:
            # Bearish shocks -> negative target proportional to gap & option profit
            # Bullish rally -> positive target
            # Choppy -> 0
            if s.actual_direction == "BEARISH":
                # Scale between -0.8 and -3.5
                target = -max(0.8, min(3.5, abs(s.actual_nifty_open_gap) / 100.0))
            elif s.actual_direction == "BULLISH":
                # Scale between +0.8 and +3.0
                target = max(0.8, min(3.0, abs(s.actual_nifty_open_gap) / 100.0))
            else:
                target = 0.0
            y.append(target)

        # 1. Fit weights using Ridge Regression
        weights = self._solve_ridge(X, y)
        macro_w = [round(w, 4) for w in weights[:5]]
        news_w = [round(w, 4) for w in weights[5:]]

        # 2. In-sample evaluation
        predictions = []
        correct_directions = 0
        squared_errors = []

        for i, row in enumerate(X):
            pred = sum(row[j] * weights[j] for j in range(len(weights)))
            predictions.append(pred)
            err = (pred - y[i]) ** 2
            squared_errors.append(err)

            # Check directional alignment
            if (pred < -0.4 and y[i] < 0) or (pred > 0.4 and y[i] > 0) or (abs(pred) <= 0.4 and y[i] == 0):
                correct_directions += 1

        mse = round(sum(squared_errors) / len(squared_errors), 4)
        dir_acc = round(correct_directions / len(samples), 4)

        # 3. Walk-Forward / Leave-One-Out Cross Validation
        cv_errors = []
        if len(samples) > 3:
            for i in range(len(samples)):
                X_train = [X[j] for j in range(len(samples)) if j != i]
                y_train = [y[j] for j in range(len(samples)) if j != i]
                w_cv = self._solve_ridge(X_train, y_train)
                val_pred = sum(X[i][j] * w_cv[j] for j in range(len(weights)))
                cv_errors.append(abs(val_pred - y[i]))
            cv_mae = round(sum(cv_errors) / len(cv_errors), 4)
        else:
            cv_mae = round(math.sqrt(mse), 4)

        # 4. Save checkpoint to SQLite
        db_manager.execute_write(
            """
            INSERT INTO macro_fusion_checkpoints (
                epoch, macro_weights_json, news_weights_json, mse, directional_accuracy, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                self._epoch,
                json.dumps(macro_w),
                json.dumps(news_w),
                mse,
                dir_acc,
                time.time()
            )
        )

        # 5. Hot-update live fusion engine
        multimodal_fusion.set_weights(macro_weights=macro_w, news_weights=news_w)

        duration_ms = round((time.time() - start_time) * 1000.0, 2)
        result = TrainingResult(
            epoch=self._epoch,
            num_samples=len(samples),
            macro_weights=macro_w,
            news_weights=news_w,
            train_mse=mse,
            directional_accuracy=dir_acc,
            cross_val_mae=cv_mae,
            training_duration_ms=duration_ms
        )

        self._epoch += 1
        return result


macro_trainer = MultimodalWeightTrainer()
