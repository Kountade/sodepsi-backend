# apps/dashboard/serializers.py
from rest_framework import serializers
from decimal import Decimal
from datetime import date, timedelta


# ============================================================
# 1. DASHBOARD SERIALIZERS - Vue d'ensemble
# ============================================================

class DashboardSummarySerializer(serializers.Serializer):
    """Résumé global du tableau de bord"""
    period = serializers.CharField()
    date_range = serializers.DictField()
    
    summary = serializers.DictField()
    metrics = serializers.DictField()
    stock = serializers.DictField()
    cash = serializers.DictField()
    recent_activities = serializers.DictField()


class RecentActivitySerializer(serializers.Serializer):
    """Activité récente"""
    id = serializers.IntegerField()
    invoice_number = serializers.CharField()
    client = serializers.CharField()
    total = serializers.FloatField()
    date = serializers.CharField()


class RecentPurchaseSerializer(serializers.Serializer):
    """Achat récent"""
    id = serializers.IntegerField()
    po_number = serializers.CharField()
    supplier = serializers.CharField()
    total = serializers.FloatField()
    date = serializers.CharField()


class DashboardMetricsSerializer(serializers.Serializer):
    """Métriques du tableau de bord"""
    products = serializers.IntegerField()
    clients = serializers.IntegerField()
    suppliers = serializers.IntegerField()
    employees = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    pending_purchase_orders = serializers.IntegerField()


class DashboardStockSerializer(serializers.Serializer):
    """État du stock"""
    total_value = serializers.FloatField()
    low_stock = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()


class DashboardCashSerializer(serializers.Serializer):
    """Trésorerie"""
    cash_balance = serializers.FloatField()
    bank_balance = serializers.FloatField()
    total = serializers.FloatField()


# ============================================================
# 2. STATISTIQUE SERIALIZERS - Graphiques et distributions
# ============================================================

class StatistiqueResponseSerializer(serializers.Serializer):
    """Réponse complète des statistiques"""
    period = serializers.CharField()
    date_range = serializers.DictField()
    charts = serializers.DictField()
    top_products = serializers.ListField()
    statistics = serializers.DictField()


class ChartDatasetSerializer(serializers.Serializer):
    """Dataset pour les graphiques"""
    label = serializers.CharField()
    data = serializers.ListField(child=serializers.FloatField())
    backgroundColor = serializers.CharField(required=False, allow_blank=True)
    borderColor = serializers.CharField(required=False, allow_blank=True)
    borderWidth = serializers.IntegerField(required=False)
    yAxisID = serializers.CharField(required=False, allow_blank=True)
    borderDash = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False
    )
    fill = serializers.BooleanField(required=False)


class SalesChartSerializer(serializers.Serializer):
    """Graphique des ventes"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = ChartDatasetSerializer(many=True)


class RevenueChartSerializer(serializers.Serializer):
    """Graphique des revenus vs dépenses"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = ChartDatasetSerializer(many=True)


class CategoryDistributionSerializer(serializers.Serializer):
    """Distribution par catégorie (Camembert)"""
    label = serializers.CharField()
    value = serializers.FloatField()
    percentage = serializers.FloatField()
    color = serializers.CharField()


class PaymentDistributionSerializer(serializers.Serializer):
    """Distribution des modes de paiement (Camembert)"""
    label = serializers.CharField()
    value = serializers.FloatField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    color = serializers.CharField()


class TopProductSerializer(serializers.Serializer):
    """Top produit"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    quantity_sold = serializers.IntegerField()
    revenue = serializers.FloatField()


class SalesStatisticsSerializer(serializers.Serializer):
    """Statistiques détaillées des ventes"""
    total = serializers.IntegerField()
    total_amount = serializers.FloatField()
    average_amount = serializers.FloatField()
    min_amount = serializers.FloatField()
    max_amount = serializers.FloatField()
    by_status = serializers.DictField()
    by_payment_status = serializers.DictField()


# ============================================================
# 3. ANALYSE SERIALIZERS - Analyses approfondies
# ============================================================

class AnalyseResponseSerializer(serializers.Serializer):
    """Réponse complète des analyses"""
    period = serializers.CharField()
    date_range = serializers.DictField()
    margin_analysis = serializers.DictField()
    monthly_trend = serializers.ListField()
    cash_flow = serializers.DictField()
    client_analysis = serializers.DictField()
    supplier_analysis = serializers.DictField()
    stock_analysis = serializers.DictField()
    period_comparison = serializers.DictField()


class MarginAnalysisSerializer(serializers.Serializer):
    """Analyse de la marge"""
    revenue = serializers.FloatField()
    cost = serializers.FloatField()
    gross_margin = serializers.FloatField()
    margin_rate = serializers.FloatField()


class MonthlyTrendSerializer(serializers.Serializer):
    """Tendance mensuelle"""
    month = serializers.CharField()
    sales_amount = serializers.FloatField()
    sales_count = serializers.IntegerField()
    purchases_amount = serializers.FloatField()
    profit = serializers.FloatField()


class CashFlowSerializer(serializers.Serializer):
    """Flux de trésorerie"""
    inflows = serializers.FloatField()
    outflows = serializers.FloatField()
    balance = serializers.FloatField()
    by_source = serializers.DictField()


class ClientAnalysisSerializer(serializers.Serializer):
    """Analyse des clients"""
    top_clients = serializers.ListField()
    total_clients = serializers.IntegerField()
    active_clients = serializers.IntegerField()
    new_clients = serializers.IntegerField()


class TopClientSerializer(serializers.Serializer):
    """Top client"""
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    orders = serializers.IntegerField()
    purchases = serializers.FloatField()


class SupplierAnalysisSerializer(serializers.Serializer):
    """Analyse des fournisseurs"""
    top_suppliers = serializers.ListField()
    total_suppliers = serializers.IntegerField()


class TopSupplierSerializer(serializers.Serializer):
    """Top fournisseur"""
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    orders = serializers.IntegerField()
    purchases = serializers.FloatField()


class StockAnalysisSerializer(serializers.Serializer):
    """Analyse du stock"""
    total_products = serializers.IntegerField()
    total_value = serializers.FloatField()
    by_category = serializers.DictField()


class PeriodComparisonSerializer(serializers.Serializer):
    """Comparaison entre périodes"""
    today = serializers.DictField()
    this_week = serializers.DictField()
    this_month = serializers.DictField()
    last_month = serializers.DictField()
    this_quarter = serializers.DictField()
    this_year = serializers.DictField()


class PeriodDataSerializer(serializers.Serializer):
    """Données d'une période"""
    revenue = serializers.FloatField()
    count = serializers.IntegerField()


# ============================================================
# 4. SERIALIZERS POUR LES GRAPHIQUES SPÉCIFIQUES
# ============================================================

class BarChartSerializer(serializers.Serializer):
    """Graphique à barres générique"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())
    options = serializers.DictField(required=False)


class PieChartSerializer(serializers.Serializer):
    """Graphique circulaire générique"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())
    options = serializers.DictField(required=False)


class LineChartSerializer(serializers.Serializer):
    """Graphique linéaire générique"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())
    options = serializers.DictField(required=False)


class DoughnutChartSerializer(serializers.Serializer):
    """Graphique en anneau générique"""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())
    options = serializers.DictField(required=False)


# ============================================================
# 5. SERIALIZERS POUR LES KPI
# ============================================================

class KpiSerializer(serializers.Serializer):
    """Indicateurs clés de performance"""
    sales = serializers.DictField()
    purchases = serializers.DictField()
    stock = serializers.DictField()
    cash = serializers.DictField()
    clients = serializers.DictField()
    employees = serializers.DictField()


class SalesKpiSerializer(serializers.Serializer):
    """KPI des ventes"""
    today = serializers.DictField()
    this_week = serializers.FloatField()
    this_month = serializers.FloatField()


class TodaySalesKpiSerializer(serializers.Serializer):
    """Ventes du jour"""
    count = serializers.IntegerField()
    amount = serializers.FloatField()


class PurchasesKpiSerializer(serializers.Serializer):
    """KPI des achats"""
    this_month = serializers.FloatField()


class StockKpiSerializer(serializers.Serializer):
    """KPI du stock"""
    total_value = serializers.FloatField()


class CashKpiSerializer(serializers.Serializer):
    """KPI de la trésorerie"""
    total = serializers.FloatField()
    cash_balance = serializers.FloatField()
    bank_balance = serializers.FloatField()


class ClientsKpiSerializer(serializers.Serializer):
    """KPI des clients"""
    total = serializers.IntegerField()
    new_this_month = serializers.IntegerField()


class EmployeesKpiSerializer(serializers.Serializer):
    """KPI des employés"""
    total = serializers.IntegerField()
    active = serializers.IntegerField()


# ============================================================
# 6. SERIALIZERS POUR LES FILTRES
# ============================================================

class DateRangeSerializer(serializers.Serializer):
    """Filtre de plage de dates"""
    start = serializers.DateField()
    end = serializers.DateField()
    period = serializers.CharField(required=False, allow_blank=True)


class PeriodFilterSerializer(serializers.Serializer):
    """Filtre de période"""
    period = serializers.ChoiceField(
        choices=[
            ('today', 'Aujourd\'hui'),
            ('week', 'Cette semaine'),
            ('month', 'Ce mois'),
            ('quarter', 'Ce trimestre'),
            ('year', 'Cette année'),
            ('last_month', 'Mois dernier')
        ],
        default='month'
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)


class ComparisonFilterSerializer(serializers.Serializer):
    """Filtre de comparaison"""
    period1 = serializers.ChoiceField(
        choices=[
            ('today', 'Aujourd\'hui'),
            ('week', 'Cette semaine'),
            ('month', 'Ce mois'),
            ('quarter', 'Ce trimestre'),
            ('year', 'Cette année'),
        ],
        default='month'
    )
    period2 = serializers.ChoiceField(
        choices=[
            ('today', 'Aujourd\'hui'),
            ('week', 'Cette semaine'),
            ('month', 'Ce mois'),
            ('quarter', 'Ce trimestre'),
            ('year', 'Cette année'),
        ],
        default='last_month'
    )


# ============================================================
# 7. SERIALIZERS POUR LES EXPORTATIONS
# ============================================================

class ExportDataSerializer(serializers.Serializer):
    """Données d'exportation"""
    format = serializers.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('pdf', 'PDF'),
            ('json', 'JSON')
        ],
        default='csv'
    )
    period = serializers.CharField(default='month')
    data_type = serializers.ChoiceField(
        choices=[
            ('summary', 'Résumé'),
            ('statistics', 'Statistiques'),
            ('analyses', 'Analyses'),
            ('all', 'Tout')
        ],
        default='summary'
    )


class ExportSummarySerializer(serializers.Serializer):
    """Résumé pour exportation"""
    period = serializers.CharField()
    generated_at = serializers.DateTimeField()
    data = serializers.DictField()


# ============================================================
# 8. SERIALIZERS POUR LES ALERTES
# ============================================================

class AlertSerializer(serializers.Serializer):
    """Alerte du système"""
    id = serializers.IntegerField()
    type = serializers.CharField()
    level = serializers.ChoiceField(
        choices=[
            ('info', 'Information'),
            ('warning', 'Avertissement'),
            ('error', 'Erreur'),
            ('critical', 'Critique')
        ]
    )
    message = serializers.CharField()
    date = serializers.DateTimeField()
    is_read = serializers.BooleanField(default=False)
    link = serializers.CharField(required=False, allow_blank=True)


class AlertListSerializer(serializers.Serializer):
    """Liste des alertes"""
    alerts = AlertSerializer(many=True)
    total = serializers.IntegerField()
    unread = serializers.IntegerField()