import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../core/api/progress_api.dart';
import '../../core/theme/app_theme.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

final checkpointsProvider =
    StateNotifierProvider<_CheckpointsNotifier, AsyncValue<List<ProgressCheckpoint>>>(
  (ref) => _CheckpointsNotifier(),
);

class _CheckpointsNotifier
    extends StateNotifier<AsyncValue<List<ProgressCheckpoint>>> {
  _CheckpointsNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final items = await ProgressApi.getCheckpoints();
      state = AsyncValue.data(items);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> delete(String id) async {
    await ProgressApi.deleteCheckpoint(id);
    await load();
  }
}

// ── Screen ────────────────────────────────────────────────────────────────────

class ProgressScreen extends ConsumerStatefulWidget {
  const ProgressScreen({super.key});

  @override
  ConsumerState<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends ConsumerState<ProgressScreen> {
  final _weightCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  bool _showForm = false;
  bool _loading = false;
  final _picker = ImagePicker();
  List<XFile> _selectedPhotos = [];

  @override
  void dispose() {
    _weightCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickPhotos() async {
    final photos = await _picker.pickMultiImage(imageQuality: 85);
    if (photos.isNotEmpty) setState(() => _selectedPhotos = photos);
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
      await ProgressApi.createCheckpoint(
        date: today,
        weightKg: double.tryParse(_weightCtrl.text),
        notes: _notesCtrl.text.trim().isEmpty ? null : _notesCtrl.text.trim(),
        photos: _selectedPhotos.map((f) => File(f.path)).toList(),
      );
      ref.invalidate(checkpointsProvider);
      if (mounted) {
        setState(() {
          _showForm = false;
          _weightCtrl.clear();
          _notesCtrl.clear();
          _selectedPhotos = [];
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Checkpoint saved!'),
            backgroundColor: AppColors.emerald,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final checkpointsAsync = ref.watch(checkpointsProvider);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title:
            const Text('Progress', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            onPressed: () => setState(() => _showForm = !_showForm),
            icon: Icon(_showForm
                ? Icons.close_rounded
                : Icons.add_rounded),
            tooltip: 'Add checkpoint',
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.emerald,
        backgroundColor: AppColors.surface,
        onRefresh: () => ref.read(checkpointsProvider.notifier).load(),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
          children: [
            // Add checkpoint form
            AnimatedSwitcher(
              duration: 300.ms,
              child: _showForm
                  ? _AddCheckpointForm(
                      key: const ValueKey('form'),
                      weightCtrl: _weightCtrl,
                      notesCtrl: _notesCtrl,
                      selectedPhotos: _selectedPhotos,
                      loading: _loading,
                      onPickPhotos: _pickPhotos,
                      onSave: _save,
                    )
                  : const SizedBox.shrink(key: ValueKey('empty')),
            ),
            if (_showForm) const SizedBox(height: 20),

            // History
            const Text('History',
                style:
                    TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),

            checkpointsAsync.when(
              loading: () => const Center(
                  child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              )),
              error: (e, _) => Text(e.toString(),
                  style: const TextStyle(color: AppColors.red)),
              data: (checkpoints) => checkpoints.isEmpty
                  ? _EmptyState()
                  : Column(
                      children: checkpoints.asMap().entries.map((entry) {
                        final i = entry.key;
                        final cp = entry.value;
                        return _CheckpointCard(
                          checkpoint: cp,
                          onDelete: () => ref
                              .read(checkpointsProvider.notifier)
                              .delete(cp.id),
                        ).animate().fadeIn(
                            delay: (i * 60).ms, duration: 300.ms);
                      }).toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Add form ──────────────────────────────────────────────────────────────────

class _AddCheckpointForm extends StatelessWidget {
  const _AddCheckpointForm({
    super.key,
    required this.weightCtrl,
    required this.notesCtrl,
    required this.selectedPhotos,
    required this.loading,
    required this.onPickPhotos,
    required this.onSave,
  });

  final TextEditingController weightCtrl;
  final TextEditingController notesCtrl;
  final List<XFile> selectedPhotos;
  final bool loading;
  final VoidCallback onPickPhotos;
  final VoidCallback onSave;

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
            const Text('New Checkpoint',
                style:
                    TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),

            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_today_outlined,
                      size: 16, color: AppColors.textMuted),
                  const SizedBox(width: 8),
                  Text(
                    DateFormat('MMMM d, yyyy').format(DateTime.now()),
                    style: const TextStyle(
                        color: AppColors.textSecondary, fontSize: 14),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            const Text('Weight (kg)',
                style: TextStyle(
                    color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: weightCtrl,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(hintText: '70.5'),
            ),
            const SizedBox(height: 12),

            const Text('Notes (optional)',
                style: TextStyle(
                    color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: notesCtrl,
              maxLines: 2,
              decoration:
                  const InputDecoration(hintText: 'How are you feeling?'),
            ),
            const SizedBox(height: 12),

            GestureDetector(
              onTap: onPickPhotos,
              child: Container(
                height: 80,
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(12),
                  border:
                      Border.all(color: AppColors.border),
                ),
                child: selectedPhotos.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.add_photo_alternate_outlined,
                                color: AppColors.textMuted, size: 28),
                            SizedBox(height: 4),
                            Text('Add progress photos',
                                style: TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 12)),
                          ],
                        ),
                      )
                    : Center(
                        child: Text(
                          '${selectedPhotos.length} photo${selectedPhotos.length > 1 ? 's' : ''} selected ✓',
                          style: const TextStyle(
                              color: AppColors.emerald, fontSize: 13),
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 16),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: loading ? null : onSave,
                child: loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Save Checkpoint'),
              ),
            ),
          ],
        ),
      ).animate().fadeIn(duration: 300.ms).slideY(begin: -0.1, end: 0);
}

// ── Checkpoint card ───────────────────────────────────────────────────────────

class _CheckpointCard extends StatelessWidget {
  const _CheckpointCard(
      {required this.checkpoint, required this.onDelete});
  final ProgressCheckpoint checkpoint;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final date = DateTime.tryParse(checkpoint.checkpointDate);
    final dateStr = date != null
        ? DateFormat('MMM d, yyyy').format(date)
        : checkpoint.checkpointDate;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          // Photo thumbnail or icon
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.surfaceElevated,
              borderRadius: BorderRadius.circular(10),
            ),
            child: checkpoint.primaryPhotoUrl != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network(
                      checkpoint.primaryPhotoUrl!,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Icon(
                          Icons.photo_outlined,
                          color: AppColors.textMuted,
                          size: 24),
                    ),
                  )
                : const Icon(Icons.photo_outlined,
                    color: AppColors.textMuted, size: 24),
          ),
          const SizedBox(width: 14),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(dateStr,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 14)),
                const SizedBox(height: 3),
                Row(
                  children: [
                    if (checkpoint.weightKg != null) ...[
                      const Icon(Icons.monitor_weight_outlined,
                          size: 13, color: AppColors.textMuted),
                      const SizedBox(width: 3),
                      Text('${checkpoint.weightKg} kg',
                          style: const TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12)),
                      const SizedBox(width: 10),
                    ],
                    if (checkpoint.photoCount > 0) ...[
                      const Icon(Icons.photo_library_outlined,
                          size: 13, color: AppColors.textMuted),
                      const SizedBox(width: 3),
                      Text('${checkpoint.photoCount} photo${checkpoint.photoCount > 1 ? 's' : ''}',
                          style: const TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12)),
                    ],
                  ],
                ),
                if (checkpoint.notes != null &&
                    checkpoint.notes!.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(checkpoint.notes!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 12)),
                ],
              ],
            ),
          ),

          IconButton(
            icon: const Icon(Icons.delete_outline_rounded,
                color: AppColors.textMuted, size: 20),
            onPressed: () => showDialog(
              context: context,
              builder: (ctx) => AlertDialog(
                backgroundColor: AppColors.surface,
                title: const Text('Delete checkpoint?'),
                content: const Text(
                    'This will remove the checkpoint and all its photos.'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Cancel'),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.red),
                    onPressed: () {
                      Navigator.pop(ctx);
                      onDelete();
                    },
                    child: const Text('Delete'),
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

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 32),
        child: const Column(
          children: [
            Icon(Icons.photo_library_outlined,
                color: AppColors.textMuted, size: 48),
            SizedBox(height: 16),
            Text('No checkpoints yet',
                style: TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w600)),
            SizedBox(height: 6),
            Text(
              'Add your first checkpoint to start\ntracking your progress over time.',
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 14,
                  height: 1.5),
            ),
          ],
        ),
      );
}
