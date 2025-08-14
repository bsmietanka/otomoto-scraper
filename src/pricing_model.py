"""Pricing model for rating car offers based on relative value within brand/model segments."""

import logging
import re

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class CarPricingModel:
    """A pricing model that predicts relative value within brand/model segments."""

    def __init__(self):
        """Initialize the pricing model."""
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.onehot_encoder = OneHotEncoder(
            sparse_output=False, handle_unknown="ignore"
        )
        self.feature_columns = []
        self.categorical_feature_names = []
        self.brand_model_avg_prices = {}
        self.logger = logging.getLogger(__name__)

    def _parse_price(self, price_str: str) -> float:
        """Parse price string like '26 900' or '22 999,99' to numeric value."""
        if pd.isna(price_str):
            return 0.0
        try:
            # Handle European decimal format (comma as decimal separator)
            # First remove spaces, then replace comma with dot for decimal
            price_clean = str(price_str).replace(" ", "").replace(",", ".")
            # Remove any remaining non-digit/non-dot characters
            price_clean = re.sub(r"[^\d.]", "", price_clean)
            return float(price_clean)
        except (ValueError, TypeError):
            return 0.0

    def _parse_mileage(self, mileage_str: str) -> float:
        """Parse mileage string like '259 000 km' to numeric value."""
        if pd.isna(mileage_str):
            return 0.0
        # Extract numbers, remove 'km' and spaces
        mileage_clean = re.sub(r"[^\d\s]", "", str(mileage_str))
        try:
            return float(mileage_clean.replace(" ", ""))
        except (ValueError, TypeError):
            return 0.0

    def _parse_engine_capacity(self, capacity_str: str) -> float:
        """Parse engine capacity string like '1 987 cm3' to numeric value."""
        if pd.isna(capacity_str):
            return 0.0
        # Extract numbers, remove 'cm3' and spaces
        capacity_clean = re.sub(r"[^\d\s]", "", str(capacity_str))
        try:
            return float(capacity_clean.replace(" ", ""))
        except (ValueError, TypeError):
            return 0.0

    def _parse_power(self, power_str: str) -> float:
        """Parse power string like '152 KM' to numeric value."""
        if pd.isna(power_str):
            return 0.0
        # Extract numbers, remove 'KM' and spaces
        power_clean = re.sub(r"[^\d\s]", "", str(power_str))
        try:
            return float(power_clean.replace(" ", ""))
        except (ValueError, TypeError):
            return 0.0

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean features for modeling."""
        data = df.copy()

        # Parse numeric columns
        data["price"] = data["Cena"].apply(self._parse_price)
        data["year"] = pd.to_numeric(data["Rok produkcji"], errors="coerce")
        data["mileage"] = data["Przebieg"].apply(self._parse_mileage)
        data["engine_capacity"] = data["Pojemność skokowa"].apply(
            self._parse_engine_capacity
        )
        data["power"] = data["Moc"].apply(self._parse_power)

        # Calculate derived features
        data["age"] = 2025 - data["year"]
        data["mileage_per_year"] = data["mileage"] / (
            data["age"] + 1
        )  # Avoid division by zero

        # Create brand_model combination for relative pricing
        data["brand_model"] = data["Marka pojazdu"] + "_" + data["Model pojazdu"]

        # Filter out invalid data - only basic sanity checks and PLN currency only
        valid_mask = (
            (data["price"] > 0)
            & (data["year"] > 1980)  # Basic sanity check
            & (data["year"] <= 2025)
            & (data["mileage"] >= 0)
            & (data["engine_capacity"] > 0)
            & (data["power"] > 0)
            & (data["Waluta"] == "PLN")  # Only PLN currency offers
        )

        data_clean = data[valid_mask].copy()

        if len(data_clean) == 0:
            raise ValueError("No valid data found after cleaning")

        # Filter out price outliers using Conservative IQR method (Q1 ± 1.0*IQR)
        # This is more conservative than standard IQR (1.5) and filters obvious data errors
        Q1 = data_clean["price"].quantile(0.25)
        Q3 = data_clean["price"].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.0 * IQR
        upper_bound = Q3 + 1.0 * IQR

        # Ensure lower bound is not negative
        lower_bound = max(0, lower_bound)

        outlier_mask = (data_clean["price"] >= lower_bound) & (
            data_clean["price"] <= upper_bound
        )

        n_before_outliers = len(data_clean)
        data_clean = data_clean[outlier_mask].copy()
        n_after_outliers = len(data_clean)

        self.logger.info(
            f"Conservative IQR outlier filtering: Q1={Q1:,.0f}, Q3={Q3:,.0f}, IQR={IQR:,.0f}"
        )
        self.logger.info(
            f"Filtered out {n_before_outliers - n_after_outliers} price outliers "
            f"(< {lower_bound:,.0f} PLN or > {upper_bound:,.0f} PLN)"
        )

        if len(data_clean) == 0:
            raise ValueError("No valid data found after outlier filtering")

        self.logger.info(
            f"Prepared {len(data_clean)} valid offers from {len(df)} total"
        )

        return data_clean

    def _encode_categorical_features(
        self, data: pd.DataFrame, fit: bool = True
    ) -> pd.DataFrame:
        """Encode categorical features using OneHotEncoder."""
        categorical_features = [
            "Marka pojazdu",
            "Rodzaj paliwa",
            "Skrzynia biegów",
            "Typ nadwozia",
        ]

        # Prepare categorical data
        categorical_data = data[categorical_features].copy()

        # Fill missing values
        for feature in categorical_features:
            if feature in categorical_data.columns:
                categorical_data[feature] = categorical_data[feature].fillna("Unknown")

        if fit:
            # Fit the encoder and transform
            encoded_array = self.onehot_encoder.fit_transform(categorical_data)
            # Store feature names for later use
            self.categorical_feature_names = self.onehot_encoder.get_feature_names_out(
                categorical_features
            )
        else:
            # Transform using fitted encoder
            encoded_array = self.onehot_encoder.transform(categorical_data)

        # Create DataFrame with encoded features
        encoded_df = pd.DataFrame(
            encoded_array, columns=self.categorical_feature_names, index=data.index
        )

        # Combine with original data (keeping original categorical columns for later use)
        result = pd.concat([data, encoded_df], axis=1)

        return result

    def _calculate_relative_price_targets(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate relative price targets based on brand/model averages."""
        data_with_targets = data.copy()

        # Calculate average price for each brand_model combination
        brand_model_stats = (
            data.groupby("brand_model").agg({"price": ["mean", "count"]}).round(0)
        )

        # Only use brand_model combinations with at least 3 cars for reliable averages
        min_samples = 3
        reliable_combinations = brand_model_stats[
            brand_model_stats[("price", "count")] >= min_samples
        ]

        # Store average prices for prediction
        self.brand_model_avg_prices = {}
        for brand_model in reliable_combinations.index:
            self.brand_model_avg_prices[brand_model] = reliable_combinations.loc[
                brand_model, ("price", "mean")
            ]

        # For combinations with enough data, use their average
        # For others, use overall brand average, then overall average
        data_with_targets["expected_price"] = 0.0

        for idx, row in data_with_targets.iterrows():
            brand_model = row["brand_model"]
            brand = row["Marka pojazdu"]

            if brand_model in self.brand_model_avg_prices:
                # Use brand_model average
                data_with_targets.loc[idx, "expected_price"] = (
                    self.brand_model_avg_prices[brand_model]
                )
            else:
                # Fallback to brand average
                brand_data = data[data["Marka pojazdu"] == brand]
                if len(brand_data) >= 5:
                    data_with_targets.loc[idx, "expected_price"] = brand_data[
                        "price"
                    ].mean()
                else:
                    # Use overall average
                    data_with_targets.loc[idx, "expected_price"] = data["price"].mean()

        # Calculate relative price (ratio to expected price)
        data_with_targets["price_ratio"] = (
            data_with_targets["price"] / data_with_targets["expected_price"]
        )

        self.logger.info(
            f"Created relative price targets for {len(self.brand_model_avg_prices)} brand/model combinations"
        )

        return data_with_targets

    def train_model(self, data: pd.DataFrame) -> dict:
        """Train the pricing model to predict relative value."""
        # Prepare features
        prepared_data = self._prepare_features(data)

        # Encode categorical features
        encoded_data = self._encode_categorical_features(prepared_data, fit=True)

        # Calculate relative price targets
        data_with_targets = self._calculate_relative_price_targets(encoded_data)

        # Select features for modeling
        # Numerical features
        numerical_features = [
            "mileage",
            "engine_capacity",
            "power",
            "age",
            "mileage_per_year",
        ]
        # Add all OneHot encoded categorical features
        categorical_features = list(self.categorical_feature_names)
        self.feature_columns = numerical_features + categorical_features

        # Prepare feature matrix and target
        X = data_with_targets[self.feature_columns]
        y = data_with_targets["price_ratio"]  # Predict relative price ratio

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        self.model.fit(X_scaled, y)

        # Calculate model performance
        predictions = self.model.predict(X_scaled)
        mse = ((predictions - y) ** 2).mean()
        rmse = mse**0.5
        mae = abs(predictions - y).mean()

        # Calculate R²
        ss_res = ((y - predictions) ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        r2 = 1 - (ss_res / ss_tot)

        # Store the prepared data for rating
        self.training_data = data_with_targets

        results = {
            "n_samples": len(data_with_targets),
            "n_features": len(self.feature_columns),
            "n_brand_models": len(self.brand_model_avg_prices),
            "rmse": rmse,
            "mae": mae,
            "r2": r2,
            "price_ratio_mean": y.mean(),
            "price_ratio_std": y.std(),
        }

        self.logger.info(f"Trained model: R² = {r2:.3f}, RMSE = {rmse:.3f}")

        return results

    def rate_offers(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        """Rate offers based on predicted vs expected relative price."""
        if data is None:
            data = self.training_data
        else:
            # Prepare new data
            prepared_data = self._prepare_features(data)
            encoded_data = self._encode_categorical_features(prepared_data, fit=False)
            data = self._calculate_relative_price_targets(encoded_data)

        # Get predictions
        X = data[self.feature_columns]
        X_scaled = self.scaler.transform(X)
        predicted_ratios = self.model.predict(X_scaled)

        # Calculate value metrics
        actual_ratios = data["price_ratio"]
        ratio_difference = actual_ratios - predicted_ratios

        # Value score: negative means car is cheaper than predicted (good deal)
        # Multiply by 100 to get percentage points
        value_score = -ratio_difference * 100

        # Create rating categories
        def categorize_deal(score):
            if score >= 15:
                return "Excellent Deal"
            elif score >= 8:
                return "Good Deal"
            elif score >= -5:
                return "Fair Price"
            elif score >= -15:
                return "Slightly Overpriced"
            else:
                return "Overpriced"

        # Create results dataframe
        results = data.copy()
        results["predicted_ratio"] = predicted_ratios
        results["predicted_price"] = results["expected_price"] * predicted_ratios
        results["actual_ratio"] = actual_ratios
        results["ratio_difference"] = ratio_difference
        results["value_score"] = value_score
        results["deal_category"] = value_score.apply(categorize_deal)

        # Sort by value score (best deals first)
        return results.sort_values("value_score", ascending=False)

    def get_model_summary(self) -> dict:
        """Get summary of the trained model."""
        if not hasattr(self, "training_data"):
            return {"error": "Model not trained yet"}

        data = self.training_data

        return {
            "total_offers": len(data),
            "price_range": f"{data['price'].min():,.0f} - {data['price'].max():,.0f} PLN",
            "year_range": f"{data['year'].min():.0f} - {data['year'].max():.0f}",
            "brands": data["Marka pojazdu"].nunique(),
            "brand_model_combinations": len(self.brand_model_avg_prices),
            "avg_price": f"{data['price'].mean():,.0f} PLN",
            "features_used": len(self.feature_columns),
        }
