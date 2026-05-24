import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title: const Text('Progress', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            onPressed: () => setState(() => _showForm = !_showForm),
            icon: Icon(_showForm ? Icons.close_rounded : Icons.add_rounded),
            tooltip: 'Add checkpoint',
          ),
        ],
      ),
      body: ListView(
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

          // Checkpoints list
          const Text('History', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),

          // Placeholder — real implementation uses CheckpointApi
          _EmptyState(),
        ],
      ),
    );
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    // TODO: call CheckpointApi.create() and upload photos
    await Future.delayed(500.ms);
    setState(() { _loading = false; _showForm = false; });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Checkpoint saved!')),
      );
    }
  }
}

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
            const Text('New Checkpoint', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),

            // Today's date
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.textMuted),
                  const SizedBox(width: 8),
                  Text(
                    DateFormat('MMMM d, yyyy').format(DateTime.now()),
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Weight
            const Text('Weight (kg)', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: weightCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(hintText: '70.5'),
            ),
            const SizedBox(height: 12),

            // Notes
            const Text('Notes (optional)', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: notesCtrl,
              maxLines: 2,
              decoration: const InputDecoration(hintText: 'How are you feeling?'),
            ),
            const SizedBox(height: 12),

            // Photo picker
            GestureDetector(
              onTap: onPickPhotos,
              child: Container(
                height: 80,
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border, style: BorderStyle.solid),
                ),
                child: selectedPhotos.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.add_photo_alternate_outlined, color: AppColors.textMuted, size: 28),
                            SizedBox(height: 4),
                            Text('Add progress photos', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                          ],
                        ),
                      )
                    : Center(
                        child: Text(
                          '${selectedPhotos.length} photo${selectedPhotos.length > 1 ? 's' : ''} selected ✓',
                          style: const TextStyle(color: AppColors.emerald, fontSize: 13),
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
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('Save Checkpoint'),
              ),
            ),
          ],
        ),
      ).animate().fadeIn(duration: 300.ms).slideY(begin: -0.1, end: 0);
}

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 32),
        child: Column(
          children: [
            Container(
              width: 72, height: 72,
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(Icons.photo_library_outlined, color: AppColors.textMuted, size: 36),
            ),
            const SizedBox(height: 16),
            const Text(
              'No checkpoints yet',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            const Text(
              'Add your first checkpoint to start\ntracking your progress over time.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.textSecondary, fontSize: 14, height: 1.5),
            ),
          ],
        ),
      );
}
