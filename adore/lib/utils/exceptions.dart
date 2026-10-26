class AppException implements Exception {
  AppException(this.message, {this.code});

  final String message;
  final String? code;

  @override
  String toString() => message;
}

class NetworkException extends AppException {
  NetworkException([super.message = 'No internet connection. Please retry.']);
}

class WeatherException extends AppException {
  WeatherException([super.message = 'Weather data could not be loaded.']);
}

class AuthException extends AppException {
  AuthException([super.message = 'Authentication failed.']);
}

class StorageException extends AppException {
  StorageException([super.message = 'Image upload failed.']);
}

class AiException extends AppException {
  AiException([
    super.message =
        'AI detection is unavailable. You can select category and color manually.',
  ]);
}

class LocationException extends AppException {
  LocationException([super.message = 'Location could not be determined.']);
}

class DatabaseException extends AppException {
  DatabaseException([super.message = 'Could not load data from the server.']);
}
