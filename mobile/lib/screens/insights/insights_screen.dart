import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/analytics_api.dart';
import '../../core/models/analytics.dart';
import '../../core/theme/app_theme.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

final _analyticsProvider = FutureProvider<AnalyticsSummary>((ref) => AnalyticsApi.getSummary());
final _trendsProvider = FutureProvider<TrendResponse>((ref) => AnalyticsApi.getTrends(days: 30));

class InsightsScreen extends ConsumerWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(_analyticsProvider);
    final trendsAsync = ref.watch(_trendsProvider);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title: const Text('Insights', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () {
              ref.invalidate(_analyticsProvider);
              ref.invalidate(_trendsProvider);
            },
          ),
        ],
      ),
      body: analyticsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(e.toString(), style: const TextStyle(color: AppColors.red))),
        data: (analytics) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
          children: [
            // ── Consistency scores ─────────────────────────────────────────
            _ConsistencyCard(analytics: analytics)
                .animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, end: 0),
            const SizedBox(height: 16),

            // ── Streak ────────────────────────────────────────────────────
            _StreakCard(streak: analytics.streak)
                .animate().fadeIn(delay: 100.ms, duration: 400.ms),
            const SizedBox(height: 16),

            // ── Calorie trend chart ────────────────────────────────────────
            trendsAsync.when(
              loading: () => _ChartSkeleton(),
              error: (_, __) => const SizedBox.shrink(),
              data: (trends) => _CalorieTrendCard(trends: trends),
            ).animate().fadeIn(delay: 200.ms, duration: 400.ms),
            const SizedBox(height: 16),

            // ── AI Pattern insights ────────────────────────────────────────
            _PatternInsightsCard(insights: analytics.patternInsights)
                .animate().fadeIn(delay: 300.ms, duration: 400.ms),
            const SizedBox(height: 16),

            // ── Weight trend ───────────────────────────────────────────────
            if (analytics.latestWeightKg != null)
              _WeightTrendCard(analytics: analytics)
                  .animate().fadeIn(delay: 400.ms, duration: 400.ms),
          ],
        ),
      ),
    );
  }
}

// ── Consistency card ──────────────────────────────────────────────────────────

class _ConsistencyCard extends StatelessWidget {
  const _ConsistencyCard({required this.analytics});
  final AnalyticsSummary analytics;

  @override
  Widget build(BuildContext context) {
    final c7 = analytics.consistency7d;
    final c30 = analytics.consistency30d;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Consistency', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: _ScoreCircle('7-Day', c7.overallScore, AppColors.emerald)),
              const SizedBox(width: 16),
              Expanded(child: _ScoreCircle('30-Day', c30.overallScore, AppColors.blue)),
            ],
          ),
          const SizedBox(height: 16),
          _ConsistencyRow('Logging', c7.loggingConsistency, c30.loggingConsistency),
          _ConsistencyRow('Calories', c7.calorieAdherence, c30.calorieAdherence),
          _ConsistencyRow('Protein', c7.proteinAdherence, c30.proteinAdherence),
          _ConsistencyRow('Workouts', c7.workoutConsistency, c30.workoutConsistency),
        ],
      ),
    );
  }
}

class _ScoreCircle extends StatelessWidget {
  const _ScoreCircle(this.label, this.score, this.color);
  final String label;
  final double score;
  final Color color;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 80, height: 80,
                child: CircularProgressIndicator(
                  value: score / 100,
                  strokeWidth: 8,
                  backgroundColor: color.withAlpha(51),
                  valueColor: AlwaysStoppedAnimation(color),
                  strokeCap: StrokeCap.round,
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${score.toInt()}',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: color),
                  ),
                  Text('%', style: TextStyle(fontSize: 11, color: color.withAlpha(179))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
        ],
      );
}

class _ConsistencyRow extends StatelessWidget {
  const _ConsistencyRow(this.label, this.score7d, this.score30d);
  final String label;
  final double score7d, score30d;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Expanded(flex: 2, child: Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13))),
            Expanded(
              flex: 3,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: score7d / 100,
                  backgroundColor: AppColors.emerald.withAlpha(51),
                  valueColor: const AlwaysStoppedAnimation(AppColors.emerald),
                  minHeight: 6,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text('${score7d.toInt()}%', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary), textAlign: TextAlign.right),
          ],
        ),
      );
}

// ── Streak card ───────────────────────────────────────────────────────────────

class _StreakCard extends StatelessWidget {
  const _StreakCard({required this.streak});
  final StreakInfo streak;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 52, height: 52,
              decoration: BoxDecoration(
                color: AppColors.amber.withAlpha(26),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(Icons.local_fire_department_rounded, color: AppColors.amber, size: 30),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${streak.currentStreakDays} day streak',
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  Text(
                    'Best: ${streak.longestStreakDays} days · ${streak.isActiveToday ? "Active today ✓" : "Log today to continue"}',
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

// ── Calorie trend chart ───────────────────────────────────────────────────────

class _CalorieTrendCard extends StatelessWidget {
  const _CalorieTrendCard({required this.trends});
  final TrendResponse trends;

  @override
  Widget build(BuildContext context) {
    final points = trends.dataPoints;
    if (points.isEmpty) return const SizedBox.shrink();

    final spots = points.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.calories);
    }).toList();

    final maxY = (points.map((p) => p.calories).reduce((a, b) => a > b ? a : b) * 1.2)
        .clamp(500.0, double.infinity);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Calorie Trend', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Text(
                'Avg: ${trends.averageCalories.toInt()} kcal',
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ],
          ),
          if (trends.calorieTarget != null)
            Text(
              'Target: ${trends.calorieTarget!.toInt()} kcal',
              style: const TextStyle(color: AppColors.emerald, fontSize: 12),
            ),
          const SizedBox(height: 16),
          SizedBox(
            height: 160,
            child: LineChart(
              LineChartData(
                minY: 0,
                maxY: maxY,
                gridData: FlGridData(
                  drawHorizontalLine: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: AppColors.border,
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                titlesData: const FlTitlesData(
                  topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                lineBarsData: [
                  // Target line (dashed)
                  if (trends.calorieTarget != null)
                    LineChartBarData(
                      spots: [
                        FlSpot(0, trends.calorieTarget!),
                        FlSpot(points.length - 1, trends.calorieTarget!),
                      ],
                      isCurved: false,
                      color: AppColors.emerald.withAlpha(102),
                      barWidth: 1.5,
                      dashArray: [6, 4],
                      dotData: const FlDotData(show: false),
                    ),
                  // Actual calorie line
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    color: AppColors.blue,
                    barWidth: 2.5,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [AppColors.blue.withAlpha(77), AppColors.blue.withAlpha(0)],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Pattern insights card ─────────────────────────────────────────────────────

class _PatternInsightsCard extends StatelessWidget {
  const _PatternInsightsCard({required this.insights});
  final List<String> insights;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppColors.purple.withAlpha(51),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.psychology_rounded, color: AppColors.purple, size: 18),
                ),
                const SizedBox(width: 10),
                const Text('AI Pattern Insights', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            if (insights.isEmpty)
              const Text(
                'Log more days to unlock AI pattern analysis.',
                style: TextStyle(color: AppColors.textMuted, fontSize: 13),
              )
            else
              ...insights.map((insight) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Padding(
                          padding: EdgeInsets.only(top: 3),
                          child: Icon(Icons.circle, size: 6, color: AppColors.purple),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(insight, style: const TextStyle(fontSize: 14, height: 1.4)),
                        ),
                      ],
                    ),
                  )),
          ],
        ),
      );
}

// ── Weight trend card ─────────────────────────────────────────────────────────

class _WeightTrendCard extends StatelessWidget {
  const _WeightTrendCard({required this.analytics});
  final AnalyticsSummary analytics;

  @override
  Widget build(BuildContext context) {
    final trend = analytics.weightTrendKg;
    final isDown = trend != null && trend < 0;
    final isUp = trend != null && trend > 0;
    final trendColor = isDown ? AppColors.emerald : isUp ? AppColors.red : AppColors.textMuted;
    final trendIcon = isDown ? Icons.trending_down_rounded : isUp ? Icons.trending_up_rounded : Icons.trending_flat_rounded;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Current Weight', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
              Text(
                '${analytics.latestWeightKg?.toStringAsFixed(1)} kg',
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const Spacer(),
          if (trend != null) ...[
            Icon(trendIcon, color: trendColor, size: 28),
            const SizedBox(width: 4),
            Text(
              '${trend > 0 ? '+' : ''}${trend.toStringAsFixed(1)} kg',
              style: TextStyle(color: trendColor, fontWeight: FontWeight.w600, fontSize: 16),
            ),
          ],
        ],
      ),
    );
  }
}

class _ChartSkeleton extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        height: 200,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: const Center(child: CircularProgressIndicator()),
      );
}
