import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class FadeSlideIn extends StatefulWidget {
  const FadeSlideIn({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.duration = AppDuration.enter,
  });

  final Widget child;
  final Duration delay;
  final Duration duration;

  @override
  State<FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<FadeSlideIn> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    Future<void>.delayed(widget.delay, () {
      if (mounted) setState(() => _visible = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedOpacity(
      opacity: _visible ? 1 : 0,
      duration: widget.duration,
      curve: Curves.easeOutCubic,
      child: AnimatedSlide(
        offset: _visible ? Offset.zero : const Offset(0, 0.05),
        duration: widget.duration,
        curve: Curves.easeOutCubic,
        child: widget.child,
      ),
    );
  }
}

class PressableScale extends StatefulWidget {
  const PressableScale({
    super.key,
    required this.child,
    this.onTap,
    this.scale = 0.97,
  });

  final Widget child;
  final VoidCallback? onTap;
  final double scale;

  @override
  State<PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<PressableScale> {
  bool _down = false;
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    final t = _down ? widget.scale : (_hover ? 1.015 : 1.0);
    return MouseRegion(
      onEnter: widget.onTap == null ? null : (_) => setState(() => _hover = true),
      onExit: widget.onTap == null ? null : (_) => setState(() => _hover = false),
      child: GestureDetector(
        onTap: widget.onTap,
        onTapDown:
            widget.onTap == null ? null : (_) => setState(() => _down = true),
        onTapUp:
            widget.onTap == null ? null : (_) => setState(() => _down = false),
        onTapCancel:
            widget.onTap == null ? null : () => setState(() => _down = false),
        child: AnimatedScale(
          scale: t,
          duration: AppDuration.fast,
          curve: Curves.easeOut,
          child: widget.child,
        ),
      ),
    );
  }
}

class SoftBackdrop extends StatelessWidget {
  const SoftBackdrop({super.key, required this.child, this.constrain = true});

  final Widget child;
  final bool constrain;

  @override
  Widget build(BuildContext context) {
    Widget content = child;
    if (constrain) {
      content = Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: AppSpace.maxContent),
          child: child,
        ),
      );
    }
    return Stack(
      children: [
        const Positioned.fill(child: _GlowField()),
        content,
      ],
    );
  }
}

class _GlowField extends StatelessWidget {
  const _GlowField();

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: dark
              ? const [Color(0xFF080B1A), Color(0xFF101328), Color(0xFF161433)]
              : const [Color(0xFFF8F6F3), Color(0xFFFFF7F4), Color(0xFFF4F0FA)],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: -80,
            right: -40,
            child: _Blob(
              color: dark ? const Color(0x33E8395A) : const Color(0x33E8395A),
              size: 220,
            ),
          ),
          Positioned(
            bottom: 80,
            left: -70,
            child: _Blob(
              color: dark ? const Color(0x337C6AF5) : const Color(0x227C6AF5),
              size: 260,
            ),
          ),
        ],
      ),
    );
  }
}

class _Blob extends StatelessWidget {
  const _Blob({required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color,
        ),
      ),
    );
  }
}

class PulseIcon extends StatefulWidget {
  const PulseIcon({
    super.key,
    required this.icon,
    this.size = 72,
    this.color,
  });

  final IconData icon;
  final double size;
  final Color? color;

  @override
  State<PulseIcon> createState() => _PulseIconState();
}

class _PulseIconState extends State<PulseIcon>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final t = 0.97 + (_controller.value * 0.06);
        return Transform.scale(scale: t, child: child);
      },
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: AppColors.primarySoft,
        ),
        child: Icon(widget.icon, size: widget.size, color: widget.color),
      ),
    );
  }
}

class SkeletonBlock extends StatefulWidget {
  const SkeletonBlock({
    super.key,
    this.height = 16,
    this.width,
    this.radius = AppRadius.sm,
  });

  final double height;
  final double? width;
  final double radius;

  @override
  State<SkeletonBlock> createState() => _SkeletonBlockState();
}

class _SkeletonBlockState extends State<SkeletonBlock>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, child) {
        return Opacity(opacity: 0.45 + (_c.value * 0.4), child: child);
      },
      child: Container(
        height: widget.height,
        width: widget.width,
        decoration: BoxDecoration(
          color: AppColors.cardBorder,
          borderRadius: BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}
