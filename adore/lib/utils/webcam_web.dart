import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';
import 'package:pointer_interceptor/pointer_interceptor.dart';

import '../theme/app_theme.dart';

Future<Uint8List?> captureWebcam(
  BuildContext context, {
  bool selfie = false,
}) {
  return Navigator.of(context).push<Uint8List>(
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (_) => _WebcamPage(selfie: selfie),
    ),
  );
}

class _WebcamPage extends StatefulWidget {
  const _WebcamPage({required this.selfie});

  final bool selfie;

  @override
  State<_WebcamPage> createState() => _WebcamPageState();
}

class _WebcamPageState extends State<_WebcamPage> {
  html.VideoElement? _video;
  html.MediaStream? _stream;
  late final String _viewType;
  String? _error;
  bool _ready = false;
  bool _snapping = false;

  @override
  void initState() {
    super.initState();
    _viewType = 'adore-webcam-${DateTime.now().microsecondsSinceEpoch}';
    _registerView();
    _start();
  }

  void _registerView() {
    final root = html.DivElement()
      ..style.position = 'relative'
      ..style.width = '100%'
      ..style.height = '100%'
      ..style.backgroundColor = '#2B211C'
      ..style.overflow = 'hidden';

    final video = html.VideoElement()
      ..autoplay = true
      ..muted = true
      ..controls = false
      ..setAttribute('playsinline', 'true')
      ..setAttribute('autoplay', 'true')
      ..setAttribute('muted', 'true');
    video.style
      ..width = '100%'
      ..height = '100%'
      ..objectFit = 'cover'
      ..backgroundColor = '#2B211C'
      ..pointerEvents = 'none';
    _video = video;

    // Flutter Cancel/Capture buttons sit below this view — do not add a
    // second HTML button bar (that caused duplicate Cancel/Capture).
    root.append(video);

    ui_web.platformViewRegistry.registerViewFactory(_viewType, (int _) => root);
  }

  Future<void> _start() async {
    try {
      final devices = html.window.navigator.mediaDevices;
      if (devices == null) {
        setState(() => _error = 'This browser cannot open the camera.');
        return;
      }
      try {
        _stream = await devices.getUserMedia({
          'audio': false,
          'video': {
            'facingMode': widget.selfie ? 'user' : {'ideal': 'environment'},
            'width': {'ideal': 1280},
            'height': {'ideal': 720},
          },
        });
      } catch (_) {
        _stream = await devices.getUserMedia({
          'audio': false,
          'video': true,
        });
      }
      final video = _video;
      if (video == null) return;
      video.srcObject = _stream;
      void markReady([_]) {
        if (!mounted || _ready) return;
        setState(() => _ready = true);
      }

      video.onLoadedMetadata.listen(markReady);
      video.onPlaying.listen(markReady);
      video.onCanPlay.listen(markReady);
      try {
        await video.play();
      } catch (_) {}
      markReady(null);
    } catch (_) {
      if (mounted) {
        setState(() {
          _error =
              'Camera permission was blocked. Allow the camera in the address bar, then try again.';
        });
      }
    }
  }

  Future<void> _snap() async {
    if (_snapping) return;
    final video = _video;
    if (video == null) return;
    setState(() => _snapping = true);
    try {
      if (video.readyState < 2 || video.videoWidth == 0) {
        await video.play();
        await Future<void>.delayed(const Duration(milliseconds: 200));
      }
      final width = video.videoWidth == 0 ? 640 : video.videoWidth;
      final height = video.videoHeight == 0 ? 480 : video.videoHeight;
      final canvas = html.CanvasElement(width: width, height: height);
      canvas.context2D.drawImageScaled(video, 0, 0, width, height);
      final dataUrl = canvas.toDataUrl('image/jpeg', 0.92);
      final comma = dataUrl.indexOf(',');
      if (comma < 0) {
        throw StateError('empty frame');
      }
      final bytes = base64Decode(dataUrl.substring(comma + 1));
      if (bytes.isEmpty) {
        throw StateError('empty photo');
      }
      _stop();
      if (mounted) Navigator.pop(context, bytes);
    } catch (_) {
      if (mounted) {
        setState(() {
          _snapping = false;
          _error = 'Could not capture that frame. Click Capture again.';
        });
      }
    }
  }

  void _stop() {
    for (final track in _stream?.getTracks() ?? []) {
      track.stop();
    }
    _video?.srcObject = null;
  }

  @override
  void dispose() {
    _stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.ink,
      appBar: AppBar(
        backgroundColor: AppColors.ink,
        foregroundColor: Colors.white,
        title: const Text('Take a photo'),
      ),
      body: Column(
        children: [
          Expanded(
            child: _error != null && !_ready
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        _error!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white, height: 1.4),
                      ),
                    ),
                  )
                : Stack(
                    children: [
                      HtmlElementView(viewType: _viewType),
                      if (_error != null)
                        Positioned(
                          left: 16,
                          right: 16,
                          top: 12,
                          child: PointerInterceptor(
                            child: Material(
                              color: AppColors.danger,
                              borderRadius: BorderRadius.circular(10),
                              child: Padding(
                                padding: const EdgeInsets.all(10),
                                child: Text(
                                  _error!,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(color: Colors.white),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
          ),
          PointerInterceptor(
            child: Material(
              color: AppColors.surface,
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () {
                            _stop();
                            Navigator.pop(context);
                          },
                          child: const Text('Cancel'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton(
                          onPressed: _ready && !_snapping ? _snap : null,
                          child: Text(_snapping ? 'Capturing…' : 'Capture'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
