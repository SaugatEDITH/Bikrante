from jet.dashboard.dashboard import Dashboard
from jet.dashboard.modules import DashboardModule
from django.utils.safestring import mark_safe

class UserRegistrationChartModule(DashboardModule):
    title = 'User Registrations (Bar Chart)'

    def render(self):
        return mark_safe("""
            <canvas id="userChart" height="180"></canvas>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const ctx = document.getElementById('userChart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar',  // Changed from 'line' to 'bar'
                    data: {
                        labels: ['Jan', 'Feb', 'Mar'],
                        datasets: [{
                            label: 'User Registrations',
                            data: [3, 7, 12],
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 1 }
                            }
                        }
                    }
                });
            </script>
        """)

class SalesChartModule(DashboardModule):
    title = 'Sales (Line Chart)'

    def render(self):
        return mark_safe("""
            <div style="margin-top: 30px;"></div>  <!-- Adds space between charts -->
            <canvas id="salesChart" height="180"></canvas>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const salesCtx = document.getElementById('salesChart').getContext('2d');
                new Chart(salesCtx, {
                    type: 'line',  // Changed from 'bar' to 'line'
                    data: {
                        labels: ['Jan', 'Feb', 'Mar','Apr'],
                        datasets: [{
                            label: 'Sales',
                            data: [15, 9, 18, 10],
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 5 }
                            }
                        }
                    }
                });
            </script>
        """)

class CustomIndexDashboard(Dashboard):
    columns = 2

    def init_with_context(self, context):
        self.children.append(UserRegistrationChartModule())
        self.children.append(SalesChartModule())
