import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/user.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _editing = false;
  bool _saving = false;
  bool _dirty = false;

  // Form state
  late TextEditingController _nameCtrl;
  late TextEditingController _ageCtrl;
  late TextEditingController _heightCtrl;
  late TextEditingController _weightCtrl;
  late TextEditingController _caloriesCtrl;
  late TextEditingController _proteinCtrl;
  late ActivityLevel _activity;
  late Goal _goal;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authProvider).user;
    _nameCtrl = TextEditingController(text: user?.displayName ?? '');
    _ageCtrl = TextEditingController(text: user?.age?.toString() ?? '');
    _heightCtrl = TextEditingController(text: user?.heightCm?.toStringAsFixed(0) ?? '');
    _weightCtrl = TextEditingController(text: user?.weightKg?.toStringAsFixed(1) ?? '');
    _caloriesCtrl = TextEditingController(text: user?.targetCalories?.toString() ?? '');
    _proteinCtrl = TextEditingController(text: user?.targetProteinG?.toStringAsFixed(0) ?? '');
    _activity = user?.activityLevel ?? ActivityLevel.moderate;
    _goal = user?.goal ?? Goal.maintain;
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _ageCtrl.dispose();
    _heightCtrl.dispose();
    _weightCtrl.dispose();
    _caloriesCtrl.dispose();
    _proteinCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref.read(authProvider.notifier).updateProfile({
        'display_name': _nameCtrl.text.trim(),
        if (_ageCtrl.text.isNotEmpty) 'age': int.tryParse(_ageCtrl.text),
        if (_heightCtrl.text.isNotEmpty) 'height_cm': double.tryParse(_heightCtrl.text),
        if (_weightCtrl.text.isNotEmpty) 'weight_kg': double.tryParse(_weightCtrl.text),
        if (_caloriesCtrl.text.isNotEmpty) 'target_calories': int.tryParse(_caloriesCtrl.text),
        if (_proteinCtrl.text.isNotEmpty) 'target_protein_g': double.tryParse(_proteinCtrl.text),
        'activity_level': _activity.value,
        'goal': _goal.value,
      });
      setState(() { _editing = false; _dirty = false; });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile saved!'), backgroundColor: AppColors.emerald),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppColors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _markDirty() => setState(() => _dirty = true);

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;
    if (user == null) return const SizedBox.shrink();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title: const Text('Profile', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          if (!_editing)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: () => setState(() => _editing = true),
              tooltip: 'Edit',
            )
          else
            TextButton(
              onPressed: () => setState(() { _editing = false; _dirty = false; }),
              child: const Text('Cancel', style: TextStyle(color: AppColors.textSecondary)),
            ),
        ],
      ),
      body: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
            children: [
              // ── Avatar ───────────────────────────────────────────────────
              Center(
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundColor: AppColors.emerald.withAlpha(51),
                      child: Text(
                        user.displayName.isNotEmpty ? user.displayName[0].toUpperCase() : '?',
                        style: const TextStyle(
                          fontSize: 32, fontWeight: FontWeight.bold, color: AppColors.emerald,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (_editing)
                      TextField(
                        controller: _nameCtrl,
                        textAlign: TextAlign.center,
                        onChanged: (_) => _markDirty(),
                        decoration: const InputDecoration(hintText: 'Your name'),
                      )
                    else
                      Text(user.displayName, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(user.email, style: const TextStyle(color: AppColors.textSecondary, fontSize: 14)),
                  ],
                ),
              ).animate().fadeIn(duration: 400.ms),
              const SizedBox(height: 28),

              // ── Body stats ───────────────────────────────────────────────
              _SectionHeader('Body Stats'),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _StatField(
                      label: 'Age',
                      ctrl: _ageCtrl,
                      suffix: 'yrs',
                      editable: _editing,
                      onChanged: _markDirty,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _StatField(
                      label: 'Height',
                      ctrl: _heightCtrl,
                      suffix: 'cm',
                      editable: _editing,
                      onChanged: _markDirty,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _StatField(
                      label: 'Weight',
                      ctrl: _weightCtrl,
                      suffix: 'kg',
                      editable: _editing,
                      onChanged: _markDirty,
                    ),
                  ),
                ],
              ).animate().fadeIn(delay: 100.ms, duration: 400.ms),
              const SizedBox(height: 24),

              // ── Goal ─────────────────────────────────────────────────────
              _SectionHeader('Goal'),
              const SizedBox(height: 10),
              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 2.4,
                children: Goal.values.map((g) {
                  final sel = g == _goal;
                  return GestureDetector(
                    onTap: _editing ? () { setState(() => _goal = g); _markDirty(); } : null,
                    child: AnimatedContainer(
                      duration: 150.ms,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: sel ? AppColors.emerald.withAlpha(26) : AppColors.surface,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: sel ? AppColors.emerald : AppColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(g.label,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: sel ? AppColors.emerald : AppColors.textPrimary,
                              )),
                          Text(g.description,
                              style: TextStyle(
                                fontSize: 11,
                                color: sel ? AppColors.emerald.withAlpha(179) : AppColors.textMuted,
                              )),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ).animate().fadeIn(delay: 150.ms, duration: 400.ms),
              const SizedBox(height: 24),

              // ── Activity level ───────────────────────────────────────────
              _SectionHeader('Activity Level'),
              const SizedBox(height: 10),
              ...ActivityLevel.values.map((a) {
                final sel = a == _activity;
                return GestureDetector(
                  onTap: _editing ? () { setState(() => _activity = a); _markDirty(); } : null,
                  child: AnimatedContainer(
                    duration: 150.ms,
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: sel ? AppColors.emerald.withAlpha(26) : AppColors.surface,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: sel ? AppColors.emerald : AppColors.border),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(a.label, style: TextStyle(
                                fontWeight: FontWeight.w500,
                                color: sel ? AppColors.emerald : AppColors.textPrimary,
                              )),
                              Text(a.description, style: TextStyle(
                                fontSize: 12,
                                color: sel ? AppColors.emerald.withAlpha(179) : AppColors.textMuted,
                              )),
                            ],
                          ),
                        ),
                        if (sel) const Icon(Icons.check_circle_rounded, color: AppColors.emerald, size: 20),
                      ],
                    ),
                  ),
                );
              }),
              const SizedBox(height: 24),

              // ── Nutrition targets ────────────────────────────────────────
              _SectionHeader('Nutrition Targets'),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _StatField(
                      label: 'Calories',
                      ctrl: _caloriesCtrl,
                      suffix: 'kcal',
                      editable: _editing,
                      onChanged: _markDirty,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _StatField(
                      label: 'Protein',
                      ctrl: _proteinCtrl,
                      suffix: 'g',
                      editable: _editing,
                      onChanged: _markDirty,
                    ),
                  ),
                ],
              ).animate().fadeIn(delay: 200.ms, duration: 400.ms),
              const SizedBox(height: 32),

              // ── Logout ───────────────────────────────────────────────────
              OutlinedButton.icon(
                onPressed: () async {
                  final confirm = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      backgroundColor: AppColors.surfaceElevated,
                      title: const Text('Sign out?'),
                      content: const Text('You will need to log in again.'),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, true),
                          child: const Text('Sign out', style: TextStyle(color: AppColors.red)),
                        ),
                      ],
                    ),
                  );
                  if (confirm == true && mounted) {
                    await ref.read(authProvider.notifier).logout();
                  }
                },
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Sign out'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.red,
                  side: const BorderSide(color: AppColors.red),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  minimumSize: const Size(double.infinity, 46),
                ),
              ),
            ],
          ),

          // ── Sticky save bar ──────────────────────────────────────────────
          if (_editing && _dirty)
            Positioned(
              bottom: 0, left: 0, right: 0,
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  border: const Border(top: BorderSide(color: AppColors.border)),
                ),
                child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('Save Changes'),
                ),
              ).animate().slideY(begin: 1, end: 0, duration: 250.ms),
            ),
        ],
      ),
    );
  }
}

// ── Shared sub-widgets ────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) => Text(
        title,
        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
      );
}

class _StatField extends StatelessWidget {
  const _StatField({
    required this.label,
    required this.ctrl,
    required this.suffix,
    required this.editable,
    required this.onChanged,
  });
  final String label;
  final TextEditingController ctrl;
  final String suffix;
  final bool editable;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: editable ? AppColors.emerald.withAlpha(76) : AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
            const SizedBox(height: 4),
            editable
                ? TextField(
                    controller: ctrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    onChanged: (_) => onChanged(),
                    decoration: InputDecoration(
                      hintText: '—',
                      suffixText: suffix,
                      suffixStyle: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      contentPadding: EdgeInsets.zero,
                      isDense: true,
                    ),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  )
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        ctrl.text.isEmpty ? '—' : ctrl.text,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(width: 2),
                      if (ctrl.text.isNotEmpty)
                        Text(suffix, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    ],
                  ),
          ],
        ),
      );
}
