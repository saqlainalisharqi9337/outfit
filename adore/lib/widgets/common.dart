import 'dart:convert';
import 'dart:typed_data';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/app_theme.dart';
import 'motion.dart';

void showImageLightbox(
  BuildContext context, {
  String? url,
  Uint8List? bytes,
}) {
  if ((url == null || url.isEmpty) && bytes == null) return;
  Navigator.of(context).push(
    PageRouteBuilder<void>(
      opaque: false,
      barrierDismissible: true,
      pageBuilder: (context, _, _) =>
          _ImageLightboxPage(url: url, bytes: bytes),
    ),
  );
}

class LoadingView extends StatelessWidget {
  const LoadingView({super.key, this.message = 'Loading…', this.skeleton = false});

  final String message;
  final bool skeleton;

  @override
  Widget build(BuildContext context) {
    if (skeleton) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpace.lg),
        child: Column(
          children: [
            SkeletonBlock(height: 140, width: double.infinity, radius: AppRadius.xl),
            const SizedBox(height: AppSpace.md),
            const SkeletonBlock(height: 18, width: 180),
            const SizedBox(height: AppSpace.sm),
            const SkeletonBlock(height: 14, width: 240),
          ],
        ),
      );
    }
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpace.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 26,
              height: 26,
              child: CircularProgressIndicator(strokeWidth: 2.4),
            ),
            const SizedBox(height: AppSpace.lg),
            Text(
              message,
              style: const TextStyle(color: AppColors.muted, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }
}

class StatusBanner extends StatelessWidget {
  const StatusBanner({
    super.key,
    required this.message,
    this.tone = StatusTone.danger,
  });

  final String message;
  final StatusTone tone;

  @override
  Widget build(BuildContext context) {
    final Color bg;
    final Color fg;
    switch (tone) {
      case StatusTone.danger:
        bg = AppColors.danger.withValues(alpha: 0.1);
        fg = AppColors.danger;
      case StatusTone.success:
        bg = AppColors.success.withValues(alpha: 0.12);
        fg = AppColors.success;
      case StatusTone.warning:
        bg = AppColors.warning.withValues(alpha: 0.12);
        fg = AppColors.warning;
    }
    return AnimatedSize(
      duration: AppDuration.fast,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Text(message, style: TextStyle(color: fg, height: 1.4)),
      ),
    );
  }
}

enum StatusTone { danger, success, warning }

class ErrorView extends StatelessWidget {
  const ErrorView({
    super.key,
    required this.message,
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 42, color: AppColors.danger),
            const SizedBox(height: AppSpace.md),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(height: 1.45),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpace.lg),
              FilledButton(onPressed: onRetry, child: const Text('Try again')),
            ],
          ],
        ),
      ),
    );
  }
}

class EmptyView extends StatelessWidget {
  const EmptyView({
    super.key,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.icon = Icons.checkroom_outlined,
  });

  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            PulseIcon(icon: icon, size: 36, color: AppColors.primary),
            const SizedBox(height: AppSpace.lg),
            Text(
              title,
              style: GoogleFonts.playfairDisplay(
                fontSize: 22,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: AppSpace.sm),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.muted, height: 1.45),
            ),
            if (onAction != null) ...[
              const SizedBox(height: AppSpace.lg),
              FilledButton(
                onPressed: onAction,
                child: Text(actionLabel ?? 'Continue'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class NetworkImageView extends StatelessWidget {
  const NetworkImageView({
    super.key,
    required this.url,
    this.height,
    this.width,
    this.fit = BoxFit.contain,
    this.borderRadius = 16,
    this.openOnTap = false,
  });

  final String url;
  final double? height;
  final double? width;
  final BoxFit fit;
  final double borderRadius;
  final bool openOnTap;

  @override
  Widget build(BuildContext context) {
    Widget image;
    if (url.isEmpty) {
      image = const Center(
        child: Icon(Icons.checkroom, color: AppColors.muted),
      );
    } else if (url.startsWith('data:')) {
      final payload = url.split(',').last;
      image = Image.memory(
        base64Decode(payload),
        fit: fit,
        width: width,
        height: height,
        alignment: Alignment.center,
      );
    } else {
      image = CachedNetworkImage(
        imageUrl: url,
        fit: fit,
        width: width,
        height: height,
        alignment: Alignment.center,
        placeholder: (_, _) => const Center(
          child: SkeletonBlock(height: 48, width: 48, radius: 24),
        ),
        errorWidget: (_, _, _) => const Center(
          child: Icon(Icons.checkroom, color: AppColors.muted, size: 36),
        ),
      );
    }
    Widget box = ColoredBox(
      color: AppColors.cardBorder.withValues(alpha: 0.55),
      child: SizedBox(height: height, width: width, child: image),
    );
    if (openOnTap && url.isNotEmpty) {
      box = GestureDetector(
        onTap: () => showImageLightbox(context, url: url),
        child: Stack(
          children: [
            box,
            const Positioned(
              right: 8,
              bottom: 8,
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Color(0x99000000),
                    shape: BoxShape.circle,
                  ),
                  child: Padding(
                    padding: EdgeInsets.all(6),
                    child: Icon(
                      Icons.open_in_full,
                      size: 14,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: box,
    );
  }
}

class PhotoTile extends StatelessWidget {
  const PhotoTile({
    super.key,
    required this.imageUrl,
    required this.title,
    this.subtitle,
    this.onTap,
    this.onDelete,
  });

  final String imageUrl;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    return PressableScale(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: AppColors.cardBorder),
          boxShadow: AppShadows.soft,
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  NetworkImageView(
                    url: imageUrl,
                    width: double.infinity,
                    fit: BoxFit.contain,
                    borderRadius: 0,
                  ),
                  if (onDelete != null)
                    Positioned(
                      top: 6,
                      right: 6,
                      child: Material(
                        color: AppColors.surface,
                        shape: const CircleBorder(),
                        child: IconButton(
                          tooltip: 'Delete this piece',
                          icon: const Icon(
                            Icons.delete_outline,
                            color: AppColors.danger,
                          ),
                          onPressed: onDelete,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, maxLines: 2, overflow: TextOverflow.ellipsis),
                  if (subtitle != null)
                    Text(
                      subtitle!,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ShortcutTile extends StatelessWidget {
  const ShortcutTile({
    super.key,
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return PressableScale(
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: AppSpace.touch, minWidth: 108),
        width: 108,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: AppColors.cardBorder),
          boxShadow: AppShadows.soft,
        ),
        child: Column(
          children: [
            Icon(icon, color: AppColors.primary),
            const SizedBox(height: 8),
            Text(
              label,
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title, {super.key, this.action, this.onAction});

  final String title;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: GoogleFonts.playfairDisplay(
              fontSize: 20,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (action != null)
          TextButton(onPressed: onAction, child: Text(action!)),
      ],
    );
  }
}

class _ImageLightboxPage extends StatelessWidget {
  const _ImageLightboxPage({this.url, this.bytes});

  final String? url;
  final Uint8List? bytes;

  @override
  Widget build(BuildContext context) {
    Widget image;
    if (bytes != null) {
      image = Image.memory(bytes!, fit: BoxFit.contain);
    } else if (url != null && url!.startsWith('data:')) {
      image = Image.memory(
        base64Decode(url!.split(',').last),
        fit: BoxFit.contain,
      );
    } else if (url != null && url!.isNotEmpty) {
      image = CachedNetworkImage(
        imageUrl: url!,
        fit: BoxFit.contain,
        placeholder: (_, _) => const Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
        errorWidget: (_, _, _) =>
            const Icon(Icons.broken_image_outlined, color: Colors.white),
      );
    } else {
      image = const Icon(Icons.checkroom, color: Colors.white);
    }

    return Scaffold(
      backgroundColor: const Color(0xF2000000),
      body: Stack(
        children: [
          Positioned.fill(
            child: InteractiveViewer(
              minScale: 0.8,
              maxScale: 5,
              child: Center(child: image),
            ),
          ),
          SafeArea(
            child: Align(
              alignment: Alignment.topRight,
              child: IconButton(
                tooltip: 'Close',
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
