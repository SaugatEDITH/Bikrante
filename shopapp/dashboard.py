from jet.dashboard.dashboard import Dashboard
from jet.dashboard.modules import DashboardModule
from django.utils.safestring import mark_safe
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Order, Product, OrderItem

def _wrap_module_html(inner_html):
    return (
        '<div style="border-radius:12px; padding:14px 14px 10px 14px;">'
        '<style>'
        '.bikrante-chart-resize{resize:both;overflow:auto;min-height:220px;min-width:280px;max-width:100%;border:1px dashed rgba(128,128,128,0.2);border-radius:10px;padding:8px;}'
        '.bikrante-chart-resize canvas{width:100% !important;height:100% !important;display:block;}'
        '</style>'
        f'{inner_html}'
        '</div>'
    )

class UserRegistrationChartModule(DashboardModule):
    title = 'User Registrations (Bar Chart)'

    def render(self):
        start_date = timezone.now() - timedelta(days=180)
        qs = (
            User.objects.filter(date_joined__gte=start_date)
            .annotate(month=TruncMonth('date_joined'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
 
        labels = [row['month'].strftime('%b %Y') for row in qs if row['month']]
        values = [row['count'] for row in qs]

        html = """
            <div class="bikrante-chart-resize">
                <canvas id="userChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const ctx = document.getElementById('userChart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: %s,
                        datasets: [{
                            label: 'User Registrations',
                            data: %s,
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true } },
                        scales: {
                            y: { beginAtZero: true, ticks: { stepSize: 1 } }
                        }
                    }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(values))
        return mark_safe(_wrap_module_html(html))

class SalesChartModule(DashboardModule):
    title = 'Sales (Line Chart)'

    def render(self):
        start_date = timezone.now() - timedelta(days=180)
        qs = (
            Order.objects.filter(created_at__gte=start_date, status='Completed')
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('total_price'))
            .order_by('month')
        )
 
        labels = [row['month'].strftime('%b %Y') for row in qs if row['month']]
        values = [float(row['total'] or 0) for row in qs]

        html = """
            <div class="bikrante-chart-resize">
                <canvas id="salesChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const salesCtx = document.getElementById('salesChart').getContext('2d');
                new Chart(salesCtx, {
                    type: 'line',
                    data: {
                        labels: %s,
                        datasets: [{
                            label: 'Sales',
                            data: %s,
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true } },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(values))
        return mark_safe(_wrap_module_html(html))


class OrdersByStatusChartModule(DashboardModule):
    title = 'Orders by Status (Pie Chart)'

    def render(self):
        qs = (
            Order.objects.values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )
        labels = [row['status'] for row in qs]
        values = [row['count'] for row in qs]

        html = """
            <div class="bikrante-chart-resize" style="height: 384px;">
                <canvas id="ordersStatusChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const ordersStatusCtx = document.getElementById('ordersStatusChart').getContext('2d');
                new Chart(ordersStatusCtx, {
                    type: 'pie',
                    data: {
                        labels: %s,
                        datasets: [{
                            label: 'Orders',
                            data: %s,
                            backgroundColor: [
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(255, 99, 132, 0.7)'
                            ],
                            borderColor: [
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(255, 99, 132, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(values))
        return mark_safe(_wrap_module_html(html))


class TopSellingProductsChartModule(DashboardModule):
    title = 'Top Selling Products (Bar Chart)'

    def render(self):
        qs = Product.objects.order_by('-sales_count').values('name', 'sales_count')[:7]
        labels = [row['name'] for row in qs]
        values = [row['sales_count'] for row in qs]

        html = """
            <div class="bikrante-chart-resize">
                <canvas id="topSellingProductsChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const topSellingCtx = document.getElementById('topSellingProductsChart').getContext('2d');
                new Chart(topSellingCtx, {
                    type: 'bar',
                    data: {
                        labels: %s,
                        datasets: [{
                            label: 'Units Sold',
                            data: %s,
                            backgroundColor: 'rgba(153, 102, 255, 0.5)',
                            borderColor: 'rgba(153, 102, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true } },
                        scales: {
                            y: { beginAtZero: true, ticks: { stepSize: 1 } }
                        }
                    }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(values))
        return mark_safe(_wrap_module_html(html))


class RevenueAndOrdersChartModule(DashboardModule):
    title = 'Revenue vs Orders (Mixed)'

    def render(self):
        start_date = timezone.now() - timedelta(days=180)
        qs = (
            Order.objects.filter(created_at__gte=start_date)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                revenue=Sum('total_price'),
                orders=Count('id'),
            )
            .order_by('month')
        )

        labels = [row['month'].strftime('%b %Y') for row in qs if row['month']]
        revenue = [float(row['revenue'] or 0) for row in qs]
        orders = [row['orders'] for row in qs]

        html = """
            <div class="bikrante-chart-resize">
                <canvas id="revenueOrdersChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const revenueOrdersCtx = document.getElementById('revenueOrdersChart').getContext('2d');
                new Chart(revenueOrdersCtx, {
                    data: {
                        labels: %s,
                        datasets: [
                            {
                                type: 'line',
                                label: 'Revenue',
                                data: %s,
                                borderColor: 'rgba(34, 197, 94, 1)',
                                backgroundColor: 'rgba(34, 197, 94, 0.15)',
                                fill: true,
                                tension: 0.3,
                                yAxisID: 'yRevenue'
                            },
                            {
                                type: 'bar',
                                label: 'Orders',
                                data: %s,
                                backgroundColor: 'rgba(59, 130, 246, 0.35)',
                                borderColor: 'rgba(59, 130, 246, 1)',
                                borderWidth: 1,
                                yAxisID: 'yOrders'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true } },
                        scales: {
                            yRevenue: { position: 'left', beginAtZero: true },
                            yOrders: { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false } }
                        }
                    }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(revenue), json.dumps(orders))
        return mark_safe(_wrap_module_html(html))


class AvgOrderValueChartModule(DashboardModule):
    title = 'Average Order Value (Line Chart)'

    def render(self):
        start_date = timezone.now() - timedelta(days=180)
        qs = (
            Order.objects.filter(created_at__gte=start_date)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(avg_value=Avg('total_price'))
            .order_by('month')
        )

        labels = [row['month'].strftime('%b %Y') for row in qs if row['month']]
        values = [float(row['avg_value'] or 0) for row in qs]

        html = """
            <div class="bikrante-chart-resize">
                <canvas id="avgOrderValueChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const avgOrderValueCtx = document.getElementById('avgOrderValueChart').getContext('2d');
                new Chart(avgOrderValueCtx, {
                    type: 'line',
                    data: {
                        labels: %s,
                        datasets: [{
                            label: 'Avg Order Value',
                            data: %s,
                            borderColor: 'rgba(245, 158, 11, 1)',
                            backgroundColor: 'rgba(245, 158, 11, 0.18)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: true } },
                        scales: { y: { beginAtZero: true } }
                    }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(values))
        return mark_safe(_wrap_module_html(html))


class LowStockProductsModule(DashboardModule):
    title = 'Low Stock Products'

    def render(self):
        products = Product.objects.filter(stock__lte=5).order_by('stock', 'name')[:10]
        rows = "".join(
            f"<tr><td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2)'>{p.name}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2);text-align:right'>{p.stock}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2);text-align:right'>{p.price}</td></tr>"
            for p in products
        )
        if not rows:
            rows = "<tr><td colspan='3' style='padding:10px;opacity:0.6'>No low-stock products.</td></tr>"

        html = (
            "<div style='overflow:auto'>"
            "<table style='width:100%;border-collapse:collapse'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Product</th>"
            "<th style='text-align:right;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Stock</th>"
            "<th style='text-align:right;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Price</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
            "</div>"
        )
        return mark_safe(_wrap_module_html(html))


class RecentUsersModule(DashboardModule):
    title = 'Recent Users'

    def render(self):
        users = User.objects.order_by('-date_joined').values('username', 'email', 'date_joined')[:8]
        rows = "".join(
            f"<tr><td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2)'>{u['username']}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2)'>{u['email']}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2);text-align:right'>{u['date_joined'].strftime('%Y-%m-%d')}</td></tr>"
            for u in users
        )
        if not rows:
            rows = "<tr><td colspan='3' style='padding:10px;opacity:0.6'>No users found.</td></tr>"

        html = (
            "<div style='overflow:auto'>"
            "<table style='width:100%;border-collapse:collapse'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Username</th>"
            "<th style='text-align:left;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Email</th>"
            "<th style='text-align:right;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Joined</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
            "</div>"
        )
        return mark_safe(_wrap_module_html(html))

class RecentOrdersModule(DashboardModule):
    title = 'Recent Orders'

    def render(self):
        orders = Order.objects.select_related('user').order_by('-created_at')[:8]
        rows = "".join(
            f"<tr><td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2)'>#{o.id}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2)'>{o.customer_name or o.user.username}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2)'>{o.status}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid rgba(128,128,128,0.2);text-align:right'>${o.total_price}</td></tr>"
            for o in orders
        )
        if not rows:
            rows = "<tr><td colspan='4' style='padding:10px;opacity:0.6'>No recent orders.</td></tr>"

        html = (
            "<div style='overflow:auto'>"
            "<table style='width:100%;border-collapse:collapse'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Order ID</th>"
            "<th style='text-align:left;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Customer</th>"
            "<th style='text-align:left;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Status</th>"
            "<th style='text-align:right;padding:8px 10px;font-weight:600;border-bottom:1px solid rgba(128,128,128,0.2)'>Total</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
            "</div>"
        )
        return mark_safe(_wrap_module_html(html))

class SalesByCategoryChartModule(DashboardModule):
    title = 'Sales by Category (Doughnut Chart)'

    def render(self):
        qs = (
            OrderItem.objects.filter(order__status='Completed')
            .values('product__category__name')
            .annotate(total_sales=Sum('quantity'))
            .order_by('-total_sales')[:6]
        )
        labels = [row['product__category__name'] for row in qs]
        values = [row['total_sales'] for row in qs]

        html = """
            <div class="bikrante-chart-resize" style="height: 300px;">
                <canvas id="salesByCategoryChart"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const categoryCtx = document.getElementById('salesByCategoryChart').getContext('2d');
                new Chart(categoryCtx, {
                    type: 'doughnut',
                    data: {
                        labels: %s,
                        datasets: [{
                            data: %s,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(153, 102, 255, 0.7)',
                                'rgba(255, 159, 64, 0.7)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
                });
            </script>
        """ % (json.dumps(labels), json.dumps(values))
        return mark_safe(_wrap_module_html(html))

class CustomIndexDashboard(Dashboard):
    columns = 2

    def init_with_context(self, context):
        self.children.append(UserRegistrationChartModule())
        self.children.append(SalesChartModule())
        self.children.append(RevenueAndOrdersChartModule())
        self.children.append(AvgOrderValueChartModule())
        self.children.append(OrdersByStatusChartModule())
        self.children.append(TopSellingProductsChartModule())
        self.children.append(SalesByCategoryChartModule())
        self.children.append(LowStockProductsModule())
        self.children.append(RecentOrdersModule())
        self.children.append(RecentUsersModule())
