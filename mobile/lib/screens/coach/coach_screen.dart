import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/coach_api.dart';
import '../../core/theme/app_theme.dart';

// ── Chat bubble model ─────────────────────────────────────────────────────────

class _Bubble {
  final String id;
  final String role;
  String content;
  bool streaming;
  final List<Map<String, dynamic>> actionEvents = [];

  _Bubble({
    required this.id,
    required this.role,
    required this.content,
    this.streaming = false,
  });
}

// ── Screen ────────────────────────────────────────────────────────────────────

class CoachScreen extends ConsumerStatefulWidget {
  const CoachScreen({super.key});

  @override
  ConsumerState<CoachScreen> createState() => _CoachScreenState();
}

class _CoachScreenState extends ConsumerState<CoachScreen> {
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<_Bubble> _bubbles = [];
  bool _loadingHistory = true;
  bool _streaming = false;
  int _msgCounter = 0;
  StreamSubscription<String>? _sub;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  @override
  void dispose() {
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _loadHistory() async {
    try {
      final msgs = await CoachApi.getHistory();
      setState(() {
        _bubbles.clear();
        for (final m in msgs) {
          _bubbles.add(_Bubble(
            id: '${_msgCounter++}',
            role: m.role,
            content: m.content,
          ));
        }
      });
    } catch (_) {
      // Non-fatal — start with empty history
    } finally {
      if (mounted) setState(() => _loadingHistory = false);
      _scrollToBottom();
    }
  }

  Future<void> _send() async {
    final text = _inputCtrl.text.trim();
    if (text.isEmpty || _streaming) return;

    _inputCtrl.clear();
    setState(() {
      _bubbles.add(_Bubble(
        id: '${_msgCounter++}',
        role: 'user',
        content: text,
      ));
      final assistantBubble = _Bubble(
        id: '${_msgCounter++}',
        role: 'assistant',
        content: '',
        streaming: true,
      );
      _bubbles.add(assistantBubble);
      _streaming = true;
    });
    _scrollToBottom();

    final assistantBubble = _bubbles.last;

    _sub = CoachApi.chat(text).listen(
      (raw) {
        if (!mounted) return;
        try {
          final event = jsonDecode(raw) as Map<String, dynamic>;
          final type = event['type'] as String?;
          if (type == 'text_delta') {
            setState(() {
              assistantBubble.content += event['content'] as String? ?? '';
            });
            _scrollToBottom();
          } else if (type == 'done') {
            setState(() {
              assistantBubble.streaming = false;
              _streaming = false;
            });
          } else if (type == 'error') {
            setState(() {
              assistantBubble.content =
                  'Error: ${event['message'] ?? 'Something went wrong'}';
              assistantBubble.streaming = false;
              _streaming = false;
            });
          } else if (type != null &&
              (type == 'food_logged' ||
                  type == 'workout_logged' ||
                  type == 'steps_logged')) {
            setState(() {
              assistantBubble.actionEvents.add(event);
            });
          }
        } catch (_) {
          // Non-JSON line — ignore
        }
      },
      onDone: () {
        if (!mounted) return;
        setState(() {
          assistantBubble.streaming = false;
          _streaming = false;
        });
      },
      onError: (e) {
        if (!mounted) return;
        setState(() {
          assistantBubble.content = 'Connection error. Please try again.';
          assistantBubble.streaming = false;
          _streaming = false;
        });
      },
    );
  }

  Future<void> _clearHistory() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Clear history?'),
        content:
            const Text('This will delete the entire conversation with Vajra.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          ElevatedButton(
            style:
                ElevatedButton.styleFrom(backgroundColor: AppColors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await CoachApi.clearHistory();
      setState(() => _bubbles.clear());
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: 200.ms,
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppColors.emerald, AppColors.blue],
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.bolt_rounded,
                  color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Vajra',
                    style: TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 16)),
                Text('AI Fitness Coach',
                    style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                        fontWeight: FontWeight.normal)),
              ],
            ),
          ],
        ),
        actions: [
          if (_bubbles.isNotEmpty)
            IconButton(
              onPressed: _clearHistory,
              icon: const Icon(Icons.delete_sweep_outlined),
              tooltip: 'Clear history',
            ),
        ],
      ),
      body: Column(
        children: [
          // Messages list
          Expanded(
            child: _loadingHistory
                ? const Center(child: CircularProgressIndicator())
                : _bubbles.isEmpty
                    ? _EmptyState(onTap: (prompt) {
                        _inputCtrl.text = prompt;
                        _send();
                      })
                    : ListView.builder(
                        controller: _scrollCtrl,
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                        itemCount: _bubbles.length,
                        itemBuilder: (context, i) {
                          final bubble = _bubbles[i];
                          return _BubbleWidget(bubble: bubble)
                              .animate()
                              .fadeIn(duration: 250.ms)
                              .slideY(begin: 0.05, end: 0);
                        },
                      ),
          ),

          // Input bar
          _InputBar(
            controller: _inputCtrl,
            streaming: _streaming,
            onSend: _send,
          ),
        ],
      ),
    );
  }
}

// ── Bubble widget ─────────────────────────────────────────────────────────────

class _BubbleWidget extends StatelessWidget {
  const _BubbleWidget({required this.bubble});
  final _Bubble bubble;

  @override
  Widget build(BuildContext context) {
    final isUser = bubble.role == 'user';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Role label
          Padding(
            padding: const EdgeInsets.only(bottom: 4, left: 4, right: 4),
            child: Text(
              isUser ? 'You' : 'Vajra',
              style: TextStyle(
                fontSize: 11,
                color: isUser ? AppColors.blue : AppColors.emerald,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),

          // Bubble
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.82,
            ),
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isUser
                  ? AppColors.blue.withAlpha(30)
                  : AppColors.surface,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(16),
                topRight: const Radius.circular(16),
                bottomLeft: Radius.circular(isUser ? 16 : 4),
                bottomRight: Radius.circular(isUser ? 4 : 16),
              ),
              border: Border.all(
                color: isUser
                    ? AppColors.blue.withAlpha(50)
                    : AppColors.border,
              ),
            ),
            child: bubble.streaming && bubble.content.isEmpty
                ? _TypingIndicator()
                : Text(
                    bubble.content,
                    style: const TextStyle(
                        fontSize: 14, height: 1.5),
                  ),
          ),

          // Action event chips
          if (bubble.actionEvents.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              children: bubble.actionEvents
                  .map((e) => _ActionChip(event: e))
                  .toList(),
            ),
          ],

          // Streaming cursor
          if (bubble.streaming && bubble.content.isNotEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 4, left: 4),
              child: _BlinkingCursor(),
            ),
        ],
      ),
    );
  }
}

class _TypingIndicator extends StatefulWidget {
  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        duration: const Duration(milliseconds: 900), vsync: this)
      ..repeat(reverse: true);
    _anim = Tween(begin: 0.3, end: 1.0).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
        opacity: _anim,
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _Dot(), SizedBox(width: 4),
            _Dot(), SizedBox(width: 4),
            _Dot(),
          ],
        ),
      );
}

class _Dot extends StatelessWidget {
  const _Dot();
  @override
  Widget build(BuildContext context) => Container(
        width: 6, height: 6,
        decoration: const BoxDecoration(
          color: AppColors.textMuted, shape: BoxShape.circle),
      );
}

class _BlinkingCursor extends StatefulWidget {
  const _BlinkingCursor();
  @override
  State<_BlinkingCursor> createState() => _BlinkingCursorState();
}

class _BlinkingCursorState extends State<_BlinkingCursor>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        duration: const Duration(milliseconds: 600), vsync: this)
      ..repeat(reverse: true);
  }
  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => FadeTransition(
        opacity: _ctrl,
        child: Container(
          width: 2, height: 14,
          color: AppColors.emerald,
        ),
      );
}

class _ActionChip extends StatelessWidget {
  const _ActionChip({required this.event});
  final Map<String, dynamic> event;

  @override
  Widget build(BuildContext context) {
    final type = event['type'] as String;
    final (label, color) = switch (type) {
      'food_logged' => ('${event['food_name']} · ${event['calories']} kcal', AppColors.emerald),
      'workout_logged' => ('Workout · ${event['calories_burned']} kcal', AppColors.blue),
      'steps_logged' => ('${event['steps']} steps logged', AppColors.amber),
      _ => (type, AppColors.textMuted),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withAlpha(25),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.check_circle_outline_rounded,
              size: 12, color: color),
          const SizedBox(width: 4),
          Text(label,
              style:
                  TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

// ── Input bar ─────────────────────────────────────────────────────────────────

class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.streaming,
    required this.onSend,
  });
  final TextEditingController controller;
  final bool streaming;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border)),
          color: AppColors.background,
        ),
        padding: EdgeInsets.only(
          left: 16,
          right: 12,
          top: 10,
          bottom: MediaQuery.of(context).padding.bottom + 10,
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                maxLines: 4,
                minLines: 1,
                textCapitalization: TextCapitalization.sentences,
                decoration: InputDecoration(
                  hintText: 'Ask Vajra anything…',
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 10),
                  filled: true,
                  fillColor: AppColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20),
                    borderSide: BorderSide.none,
                  ),
                ),
                onSubmitted: (_) => onSend(),
              ),
            ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: streaming ? null : onSend,
              child: AnimatedContainer(
                duration: 150.ms,
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: streaming
                      ? AppColors.textMuted.withAlpha(60)
                      : AppColors.emerald,
                  shape: BoxShape.circle,
                ),
                child: streaming
                    ? const Padding(
                        padding: EdgeInsets.all(10),
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.send_rounded,
                        color: Colors.white, size: 18),
              ),
            ),
          ],
        ),
      );
}

// ── Empty state with starter prompts ─────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onTap});
  final void Function(String prompt) onTap;

  static const _starters = [
    'What should I eat today given my goals?',
    'Suggest a workout for today',
    'How am I doing on my protein target this week?',
    'Log 3 rotis with dal and sabzi for lunch',
  ];

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72, height: 72,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.emerald, AppColors.blue],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.bolt_rounded,
                    color: Colors.white, size: 36),
              ),
              const SizedBox(height: 16),
              const Text('Vajra',
                  style: TextStyle(
                      fontSize: 22, fontWeight: FontWeight.bold)),
              const SizedBox(height: 6),
              const Text(
                'Your AI fitness coach. Ask anything about your diet, workouts, or progress.',
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 14,
                    height: 1.5),
              ),
              const SizedBox(height: 24),
              ..._starters.map((s) => GestureDetector(
                    onTap: () => onTap(s),
                    child: Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(s,
                          style: const TextStyle(
                              fontSize: 13,
                              color: AppColors.textSecondary)),
                    ),
                  )),
            ],
          ),
        ),
      );
}
