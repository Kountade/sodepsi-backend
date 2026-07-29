from django.shortcuts import render

# Create your views here.
# apps/dashboard/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, Avg, F, DecimalField, Min, Max
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import calendar

from users.models import CustomUser
from produits_stocks.models import Product, Lot, Stock, Category, StockMovement
from achats_fournisseurs.models import Supplier, PurchaseOrder, PurchaseOrderLine
from ventes_clients.models import Client, Vente, LigneVente, Paiement, Facture, Devis
from tresorerie.models import MouvementTresorerie, Caisse, CompteBancaire


# ============================================================
# VIEWSET 1: DASHBOARD - Vue d'ensemble
# ============================================================

class DashboardViewSet(viewsets.ViewSet):
    """
    Vue d'ensemble du tableau de bord
    Endpoint: /api/dashboard/
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_date_range(self, period='month'):
        """Retourne les dates de début et fin selon la période"""
        today = timezone.now().date()

        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'quarter':
            month = today.month
            quarter_month = ((month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif period == 'last_month':
            first_day = today.replace(day=1)
            last_day = first_day - timedelta(days=1)
            start_date = last_day.replace(day=1)
            end_date = last_day
        else:
            start_date = today - timedelta(days=30)
            end_date = today

        return start_date, end_date

    def list(self, request):
        """
        GET /api/dashboard/
        Vue d'ensemble du tableau de bord
        """
        period = request.query_params.get('period', 'month')
        start_date, end_date = self._get_date_range(period)

        # === 1. RÉSUMÉ GLOBAL ===
        sales = Vente.objects.filter(
            status__in=['confirmed', 'paid', 'delivered'],
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date
        )
        total_sales = sales.count()
        total_revenue = sales.aggregate(total=Sum('total'))[
            'total'] or Decimal('0')

        # Période précédente pour comparaison
        delta = end_date - start_date
        prev_start = start_date - delta - timedelta(days=1)
        prev_end = start_date - timedelta(days=1)

        prev_sales = Vente.objects.filter(
            status__in=['confirmed', 'paid', 'delivered'],
            sale_date__date__gte=prev_start,
            sale_date__date__lte=prev_end
        )
        prev_revenue = prev_sales.aggregate(total=Sum('total'))[
            'total'] or Decimal('0')
        prev_sales_count = prev_sales.count()

        # Dépenses (achats)
        purchases = PurchaseOrder.objects.filter(
            status__in=['received', 'confirmed'],
            order_date__date__gte=start_date,
            order_date__date__lte=end_date
        )
        total_purchases = purchases.count()
        total_expenses = purchases.aggregate(total=Sum('total'))[
            'total'] or Decimal('0')

        # Bénéfice
        net_profit = total_revenue - total_expenses
        profit_margin = (net_profit / total_revenue *
                         100) if total_revenue > 0 else 0

        # Évolution
        revenue_change = ((total_revenue - prev_revenue) /
                          prev_revenue * 100) if prev_revenue > 0 else 0
        sales_change = ((total_sales - prev_sales_count) /
                        prev_sales_count * 100) if prev_sales_count > 0 else 0

        # === 2. MÉTRIQUES RAPIDES ===
        total_products = Product.objects.filter(status='active').count()
        total_clients = Client.objects.filter(statut='actif').count()
        total_suppliers = Supplier.objects.filter(is_active=True).count()
        total_employees = CustomUser.objects.filter(is_active=True).count()

        # Commandes en attente
        pending_orders = Vente.objects.filter(status='draft').count()
        pending_purchase_orders = PurchaseOrder.objects.filter(
            status__in=['draft', 'sent', 'confirmed']
        ).count()

        # Stock
        total_stock_value = Decimal('0')
        low_stock_products = 0
        out_of_stock_products = 0

        for product in Product.objects.filter(status='active'):
            current_stock = product.current_stock
            total_stock_value += current_stock * product.purchase_price
            if current_stock <= 0:
                out_of_stock_products += 1
            elif current_stock <= product.min_stock:
                low_stock_products += 1

        # === 3. TRÉSORERIE RAPIDE ===
        cash_balance = Caisse.objects.filter(is_active=True).aggregate(
            total=Sum('solde_actuel'))['total'] or Decimal('0')
        bank_balance = CompteBancaire.objects.filter(is_active=True).aggregate(
            total=Sum('solde_actuel'))['total'] or Decimal('0')

        # === 4. DERNIÈRES ACTIVITÉS ===
        recent_sales = Vente.objects.filter(
            status__in=['confirmed', 'paid', 'delivered']
        ).order_by('-sale_date')[:5]

        recent_sales_data = []
        for sale in recent_sales:
            recent_sales_data.append({
                'id': sale.id,
                'invoice_number': sale.invoice_number,
                'client': sale.client_name,
                'total': float(sale.total),
                'date': sale.sale_date.strftime('%Y-%m-%d %H:%M')
            })

        recent_purchases = PurchaseOrder.objects.filter(
            status__in=['received', 'confirmed']
        ).order_by('-order_date')[:5]

        recent_purchases_data = []
        for purchase in recent_purchases:
            recent_purchases_data.append({
                'id': purchase.id,
                'po_number': purchase.po_number,
                'supplier': purchase.supplier.name if purchase.supplier else 'N/A',
                'total': float(purchase.total),
                'date': purchase.order_date.strftime('%Y-%m-%d %H:%M')
            })

        response_data = {
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_revenue': float(total_revenue),
                'total_expenses': float(total_expenses),
                'net_profit': float(net_profit),
                'profit_margin': round(profit_margin, 2),
                'total_orders': total_sales,
                'total_purchase_orders': total_purchases,
                'revenue_change': round(revenue_change, 2),
                'orders_change': round(sales_change, 2)
            },
            'metrics': {
                'products': total_products,
                'clients': total_clients,
                'suppliers': total_suppliers,
                'employees': total_employees,
                'pending_orders': pending_orders,
                'pending_purchase_orders': pending_purchase_orders
            },
            'stock': {
                'total_value': float(total_stock_value),
                'low_stock': low_stock_products,
                'out_of_stock': out_of_stock_products
            },
            'cash': {
                'cash_balance': float(cash_balance),
                'bank_balance': float(bank_balance),
                'total': float(cash_balance + bank_balance)
            },
            'recent_activities': {
                'sales': recent_sales_data,
                'purchases': recent_purchases_data
            }
        }

        return Response(response_data)


# ============================================================
# VIEWSET 2: STATISTIQUE - Graphiques et distributions
# ============================================================

class StatistiqueViewSet(viewsets.ViewSet):
    """
    Statistiques avec graphiques et distributions
    Endpoint: /api/statistique/
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_date_range(self, period='month'):
        """Retourne les dates de début et fin selon la période"""
        today = timezone.now().date()

        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'quarter':
            month = today.month
            quarter_month = ((month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif period == 'last_month':
            first_day = today.replace(day=1)
            last_day = first_day - timedelta(days=1)
            start_date = last_day.replace(day=1)
            end_date = last_day
        else:
            start_date = today - timedelta(days=30)
            end_date = today

        return start_date, end_date

    def list(self, request):
        """
        GET /api/statistique/
        Statistiques détaillées avec graphiques
        """
        period = request.query_params.get('period', 'month')
        start_date, end_date = self._get_date_range(period)

        # === 1. GRAPHIQUE DES VENTES ===
        sales_chart = self._get_sales_chart(start_date, end_date)

        # === 2. GRAPHIQUE REVENUS VS DÉPENSES ===
        revenue_chart = self._get_revenue_vs_expenses(start_date, end_date)

        # === 3. DISTRIBUTION PAR CATÉGORIE (Camembert) ===
        category_distribution = self._get_category_distribution(
            start_date, end_date)

        # === 4. DISTRIBUTION DES MODES DE PAIEMENT (Camembert) ===
        payment_distribution = self._get_payment_distribution(
            start_date, end_date)

        # === 5. TOP PRODUITS ===
        top_products = self._get_top_products(start_date, end_date, limit=5)

        # === 6. STATISTIQUES DÉTAILLÉES ===
        sales_stats = self._get_sales_statistics(start_date, end_date)

        response_data = {
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'charts': {
                'sales_chart': sales_chart,
                'revenue_chart': revenue_chart,
                'category_distribution': category_distribution,
                'payment_distribution': payment_distribution
            },
            'top_products': top_products,
            'statistics': sales_stats
        }

        return Response(response_data)

    # ============ MÉTHODES AUXILIAIRES ============

    def _get_sales_chart(self, start_date, end_date):
        """Graphique des ventes"""
        days = (end_date - start_date).days + 1

        if days > 90:
            return self._get_sales_by_month(start_date, end_date)
        elif days > 30:
            return self._get_sales_by_week(start_date, end_date)
        else:
            return self._get_sales_by_day(start_date, end_date)

    def _get_sales_by_day(self, start_date, end_date):
        """Ventes groupées par jour"""
        labels = []
        sales_data = []
        revenue_data = []

        current = start_date
        while current <= end_date:
            labels.append(current.strftime('%d %b'))

            sales_day = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date=current
            )
            sales_data.append(sales_day.count())
            revenue_data.append(
                float(sales_day.aggregate(total=Sum('total'))
                      ['total'] or Decimal('0'))
            )

            current += timedelta(days=1)

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Nombre de ventes',
                    'data': sales_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgb(54, 162, 235)',
                    'borderWidth': 2
                },
                {
                    'label': 'Chiffre d\'affaires (FCFA)',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgb(75, 192, 192)',
                    'borderWidth': 2,
                    'yAxisID': 'y1'
                }
            ]
        }

    def _get_sales_by_week(self, start_date, end_date):
        """Ventes groupées par semaine"""
        labels = []
        sales_data = []
        revenue_data = []

        current = start_date
        week_num = 1
        while current <= end_date:
            week_end = current + timedelta(days=6)
            if week_end > end_date:
                week_end = end_date

            labels.append(f'Sem. {week_num}')

            sales_week = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date__gte=current,
                sale_date__date__lte=week_end
            )
            sales_data.append(sales_week.count())
            revenue_data.append(
                float(sales_week.aggregate(total=Sum('total'))
                      ['total'] or Decimal('0'))
            )

            current = week_end + timedelta(days=1)
            week_num += 1

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Nombre de ventes',
                    'data': sales_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgb(54, 162, 235)',
                    'borderWidth': 2
                },
                {
                    'label': 'Chiffre d\'affaires (FCFA)',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgb(75, 192, 192)',
                    'borderWidth': 2,
                    'yAxisID': 'y1'
                }
            ]
        }

    def _get_sales_by_month(self, start_date, end_date):
        """Ventes groupées par mois"""
        labels = []
        sales_data = []
        revenue_data = []

        current = start_date.replace(day=1)
        while current <= end_date:
            month_end = current.replace(day=1)
            if month_end.month == 12:
                month_end = month_end.replace(
                    year=month_end.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_end.replace(
                    month=month_end.month + 1, day=1) - timedelta(days=1)

            if month_end > end_date:
                month_end = end_date

            labels.append(current.strftime('%b %Y'))

            sales_month = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date__gte=current,
                sale_date__date__lte=month_end
            )
            sales_data.append(sales_month.count())
            revenue_data.append(
                float(sales_month.aggregate(total=Sum('total'))
                      ['total'] or Decimal('0'))
            )

            if current.month == 12:
                current = current.replace(
                    year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Nombre de ventes',
                    'data': sales_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgb(54, 162, 235)',
                    'borderWidth': 2
                },
                {
                    'label': 'Chiffre d\'affaires (FCFA)',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgb(75, 192, 192)',
                    'borderWidth': 2,
                    'yAxisID': 'y1'
                }
            ]
        }

    def _get_revenue_vs_expenses(self, start_date, end_date):
        """Revenus vs Dépenses"""
        days = (end_date - start_date).days + 1

        if days > 60:
            return self._get_revenue_by_month(start_date, end_date)
        else:
            return self._get_revenue_by_week(start_date, end_date)

    def _get_revenue_by_week(self, start_date, end_date):
        """Revenus groupés par semaine"""
        labels = []
        revenue_data = []
        expenses_data = []
        profit_data = []

        current = start_date
        week_num = 1
        while current <= end_date:
            week_end = current + timedelta(days=6)
            if week_end > end_date:
                week_end = end_date

            labels.append(f'Sem. {week_num}')

            revenue = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date__gte=current,
                sale_date__date__lte=week_end
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')

            expenses = PurchaseOrder.objects.filter(
                status__in=['received', 'confirmed'],
                order_date__date__gte=current,
                order_date__date__lte=week_end
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')

            revenue_data.append(float(revenue))
            expenses_data.append(float(expenses))
            profit_data.append(float(revenue - expenses))

            current = week_end + timedelta(days=1)
            week_num += 1

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenus',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgb(54, 162, 235)',
                    'borderWidth': 2
                },
                {
                    'label': 'Dépenses',
                    'data': expenses_data,
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    'borderColor': 'rgb(255, 99, 132)',
                    'borderWidth': 2
                },
                {
                    'label': 'Bénéfice',
                    'data': profit_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgb(75, 192, 192)',
                    'borderWidth': 2,
                    'borderDash': [5, 5]
                }
            ]
        }

    def _get_revenue_by_month(self, start_date, end_date):
        """Revenus groupés par mois"""
        labels = []
        revenue_data = []
        expenses_data = []
        profit_data = []

        current = start_date.replace(day=1)
        while current <= end_date:
            month_end = current.replace(day=1)
            if month_end.month == 12:
                month_end = month_end.replace(
                    year=month_end.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_end.replace(
                    month=month_end.month + 1, day=1) - timedelta(days=1)

            if month_end > end_date:
                month_end = end_date

            labels.append(current.strftime('%b %Y'))

            revenue = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date__gte=current,
                sale_date__date__lte=month_end
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')

            expenses = PurchaseOrder.objects.filter(
                status__in=['received', 'confirmed'],
                order_date__date__gte=current,
                order_date__date__lte=month_end
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')

            revenue_data.append(float(revenue))
            expenses_data.append(float(expenses))
            profit_data.append(float(revenue - expenses))

            if current.month == 12:
                current = current.replace(
                    year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenus',
                    'data': revenue_data,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgb(54, 162, 235)',
                    'borderWidth': 2
                },
                {
                    'label': 'Dépenses',
                    'data': expenses_data,
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    'borderColor': 'rgb(255, 99, 132)',
                    'borderWidth': 2
                },
                {
                    'label': 'Bénéfice',
                    'data': profit_data,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgb(75, 192, 192)',
                    'borderWidth': 2,
                    'borderDash': [5, 5]
                }
            ]
        }

    def _get_category_distribution(self, start_date, end_date):
        """Distribution des ventes par catégorie (Camembert)"""
        category_sales = (
            LigneVente.objects
            .filter(
                sale__status__in=['confirmed', 'paid', 'delivered'],
                sale__sale_date__date__gte=start_date,
                sale__sale_date__date__lte=end_date
            )
            .select_related('product__category')
            .values('product__category_id', 'product__category__name')
            .annotate(
                total_sales=Sum('quantity'),
                total_revenue=Sum('total')
            )
            .order_by('-total_revenue')
        )

        total_revenue = sum(item['total_revenue'] or Decimal('0')
                            for item in category_sales)

        result = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                  '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF']

        for i, item in enumerate(category_sales):
            revenue = item['total_revenue'] or Decimal('0')
            percentage = (revenue / total_revenue *
                          100) if total_revenue > 0 else 0
            result.append({
                'label': item['product__category__name'] or 'Sans catégorie',
                'value': float(revenue),
                'percentage': round(percentage, 2),
                'color': colors[i % len(colors)]
            })

        return result

    def _get_payment_distribution(self, start_date, end_date):
        """Distribution des modes de paiement (Camembert)"""
        paiements = Paiement.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date
        )

        methods_data = paiements.values('method').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')

        total_amount = sum(item['total_amount'] or Decimal('0')
                           for item in methods_data)

        result = []
        colors = ['#4BC0C0', '#FF6384', '#FFCE56',
                  '#36A2EB', '#9966FF', '#FF9F40']

        for i, item in enumerate(methods_data):
            amount = item['total_amount'] or Decimal('0')
            percentage = (amount / total_amount *
                          100) if total_amount > 0 else 0

            method_labels = {
                'cash': 'Espèces',
                'card': 'Carte bancaire',
                'check': 'Chèque',
                'transfer': 'Virement',
                'mobile_money': 'Mobile Money',
                'credit': 'Crédit'
            }

            result.append({
                'label': method_labels.get(item['method'], item['method'] or 'Non spécifié'),
                'value': float(amount),
                'count': item['count'] or 0,
                'percentage': round(percentage, 2),
                'color': colors[i % len(colors)]
            })

        return result

    def _get_top_products(self, start_date, end_date, limit=5):
        """Top produits"""
        top_products = (
            LigneVente.objects
            .filter(
                sale__status__in=['confirmed', 'paid', 'delivered'],
                sale__sale_date__date__gte=start_date,
                sale__sale_date__date__lte=end_date
            )
            .values('product_id', 'product__name', 'product__code')
            .annotate(
                quantity_sold=Sum('quantity'),
                total_revenue=Sum('total')
            )
            .order_by('-total_revenue')[:limit]
        )

        result = []
        for item in top_products:
            result.append({
                'id': item['product_id'],
                'name': item['product__name'],
                'code': item['product__code'],
                'quantity_sold': item['quantity_sold'] or 0,
                'revenue': float(item['total_revenue'] or Decimal('0'))
            })

        return result

    def _get_sales_statistics(self, start_date, end_date):
        """Statistiques détaillées des ventes"""
        sales = Vente.objects.filter(
            status__in=['confirmed', 'paid', 'delivered'],
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date
        )

        total = sales.count()
        total_amount = sales.aggregate(total=Sum('total'))[
            'total'] or Decimal('0')
        avg_amount = total_amount / total if total > 0 else 0

        by_status = {}
        for status_choice in Vente.STATUS_CHOICES:
            code = status_choice[0]
            count = sales.filter(status=code).count()
            if count > 0:
                by_status[code] = count

        by_payment = {}
        for payment_choice in Vente.PAYMENT_STATUS_CHOICES:
            code = payment_choice[0]
            count = sales.filter(payment_status=code).count()
            if count > 0:
                by_payment[code] = count

        return {
            'total': total,
            'total_amount': float(total_amount),
            'average_amount': float(avg_amount),
            'min_amount': float(sales.aggregate(min=Min('total'))['min'] or 0),
            'max_amount': float(sales.aggregate(max=Max('total'))['max'] or 0),
            'by_status': by_status,
            'by_payment_status': by_payment
        }


# ============================================================
# VIEWSET 3: ANALYSE - Analyses approfondies
# ============================================================

class AnalyseViewSet(viewsets.ViewSet):
    """
    Analyses approfondies et comparaisons
    Endpoint: /api/analyse/
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_date_range(self, period='month'):
        """Retourne les dates de début et fin selon la période"""
        today = timezone.now().date()

        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'quarter':
            month = today.month
            quarter_month = ((month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif period == 'last_month':
            first_day = today.replace(day=1)
            last_day = first_day - timedelta(days=1)
            start_date = last_day.replace(day=1)
            end_date = last_day
        else:
            start_date = today - timedelta(days=30)
            end_date = today

        return start_date, end_date

    def list(self, request):
        """
        GET /api/analyse/
        Analyses approfondies avec comparaisons
        """
        period = request.query_params.get('period', 'month')
        start_date, end_date = self._get_date_range(period)

        # === 1. ANALYSE DE LA MARGE ===
        margin_analysis = self._get_margin_analysis(start_date, end_date)

        # === 2. ÉVOLUTION MENSUELLE ===
        monthly_trend = self._get_monthly_trend()

        # === 3. FLUX DE TRÉSORERIE ===
        cash_flow = self._get_cash_flow(start_date, end_date)

        # === 4. ANALYSE DES CLIENTS ===
        client_analysis = self._get_client_analysis(start_date, end_date)

        # === 5. ANALYSE DES FOURNISSEURS ===
        supplier_analysis = self._get_supplier_analysis(start_date, end_date)

        # === 6. ANALYSE DU STOCK ===
        stock_analysis = self._get_stock_analysis()

        # === 7. COMPARAISON PÉRIODES ===
        period_comparison = self._get_period_comparison()

        response_data = {
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'margin_analysis': margin_analysis,
            'monthly_trend': monthly_trend,
            'cash_flow': cash_flow,
            'client_analysis': client_analysis,
            'supplier_analysis': supplier_analysis,
            'stock_analysis': stock_analysis,
            'period_comparison': period_comparison
        }

        return Response(response_data)

    # ============ MÉTHODES AUXILIAIRES ============

    def _get_margin_analysis(self, start_date, end_date):
        """Analyse de la marge"""
        revenue = Vente.objects.filter(
            status__in=['confirmed', 'paid', 'delivered'],
            sale_date__date__gte=start_date,
            sale_date__date__lte=end_date
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        cost = PurchaseOrder.objects.filter(
            status__in=['received', 'confirmed'],
            order_date__date__gte=start_date,
            order_date__date__lte=end_date
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        gross_margin = revenue - cost
        margin_rate = (gross_margin / revenue * 100) if revenue > 0 else 0

        return {
            'revenue': float(revenue),
            'cost': float(cost),
            'gross_margin': float(gross_margin),
            'margin_rate': round(margin_rate, 2)
        }

    def _get_monthly_trend(self):
        """Tendance mensuelle sur l'année en cours"""
        year = timezone.now().year
        result = []

        for month in range(1, 13):
            sales_month = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__month=month,
                sale_date__year=year
            )
            sales_amount = sales_month.aggregate(total=Sum('total'))[
                'total'] or Decimal('0')
            sales_count = sales_month.count()

            purchases_month = PurchaseOrder.objects.filter(
                status__in=['received', 'confirmed'],
                order_date__month=month,
                order_date__year=year
            )
            purchases_amount = purchases_month.aggregate(
                total=Sum('total'))['total'] or Decimal('0')

            result.append({
                'month': calendar.month_name[month],
                'sales_amount': float(sales_amount),
                'sales_count': sales_count,
                'purchases_amount': float(purchases_amount),
                'profit': float(sales_amount - purchases_amount)
            })

        return result

    def _get_cash_flow(self, start_date, end_date):
        """Flux de trésorerie"""
        mouvements = MouvementTresorerie.objects.filter(
            status='effectue',
            date_mouvement__date__gte=start_date,
            date_mouvement__date__lte=end_date
        )

        inflows = mouvements.filter(type_mouvement='encaissement').aggregate(
            total=Sum('montant'))['total'] or Decimal('0')
        outflows = mouvements.filter(type_mouvement='decaissement').aggregate(
            total=Sum('montant'))['total'] or Decimal('0')

        # Par type de source
        by_source = {}
        for source_type in MouvementTresorerie.SOURCE_TYPE:
            code = source_type[0]
            total = mouvements.filter(source_type=code).aggregate(
                total=Sum('montant'))['total'] or Decimal('0')
            if total > 0:
                by_source[code] = float(total)

        return {
            'inflows': float(inflows),
            'outflows': float(outflows),
            'balance': float(inflows - outflows),
            'by_source': by_source
        }

    def _get_client_analysis(self, start_date, end_date):
        """Analyse des clients"""
        top_clients = (
            Vente.objects
            .filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date
            )
            .values('client_id', 'client_name')
            .annotate(
                total_orders=Count('id'),
                total_purchases=Sum('total')
            )
            .order_by('-total_purchases')[:5]
        )

        total_clients = Client.objects.count()
        active_clients = Client.objects.filter(statut='actif').count()

        new_clients = Client.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).count()

        return {
            'top_clients': [
                {
                    'id': c['client_id'],
                    'name': c['client_name'] or 'Anonyme',
                    'orders': c['total_orders'] or 0,
                    'purchases': float(c['total_purchases'] or Decimal('0'))
                }
                for c in top_clients
            ],
            'total_clients': total_clients,
            'active_clients': active_clients,
            'new_clients': new_clients
        }

    def _get_supplier_analysis(self, start_date, end_date):
        """Analyse des fournisseurs"""
        top_suppliers = (
            PurchaseOrder.objects
            .filter(
                status__in=['received', 'confirmed'],
                order_date__date__gte=start_date,
                order_date__date__lte=end_date
            )
            .values('supplier_id', 'supplier__name')
            .annotate(
                total_orders=Count('id'),
                total_purchases=Sum('total')
            )
            .order_by('-total_purchases')[:5]
        )

        total_suppliers = Supplier.objects.filter(is_active=True).count()

        return {
            'top_suppliers': [
                {
                    'id': s['supplier_id'],
                    'name': s['supplier__name'] or 'N/A',
                    'orders': s['total_orders'] or 0,
                    'purchases': float(s['total_purchases'] or Decimal('0'))
                }
                for s in top_suppliers
            ],
            'total_suppliers': total_suppliers
        }

    def _get_stock_analysis(self):
        """Analyse du stock"""
        total_products = Product.objects.filter(status='active').count()
        total_value = Decimal('0')
        by_category = {}

        for product in Product.objects.filter(status='active'):
            stock_value = product.current_stock * product.purchase_price
            total_value += stock_value

            if product.category:
                cat_name = product.category.name
                if cat_name not in by_category:
                    by_category[cat_name] = Decimal('0')
                by_category[cat_name] += stock_value

        return {
            'total_products': total_products,
            'total_value': float(total_value),
            'by_category': {k: float(v) for k, v in by_category.items()}
        }

    def _get_period_comparison(self):
        """Comparaison entre différentes périodes"""
        today = timezone.now().date()

        periods = {
            'today': today,
            'this_week': today - timedelta(days=7),
            'this_month': today.replace(day=1),
            'last_month': (today.replace(day=1) - timedelta(days=1)).replace(day=1),
            'this_quarter': today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1),
            'this_year': today.replace(month=1, day=1)
        }

        result = {}

        for period_name, start_date in periods.items():
            if period_name == 'today':
                end_date = today
            else:
                end_date = today

            sales = Vente.objects.filter(
                status__in=['confirmed', 'paid', 'delivered'],
                sale_date__date__gte=start_date,
                sale_date__date__lte=end_date
            )

            result[period_name] = {
                'revenue': float(sales.aggregate(total=Sum('total'))['total'] or Decimal('0')),
                'count': sales.count()
            }

        return result
