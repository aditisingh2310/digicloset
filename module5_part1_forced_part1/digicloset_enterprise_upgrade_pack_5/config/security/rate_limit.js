// config/security/rate_limit.js
import rateLimit from 'express-rate-limit';

export const apiRateLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  keyGenerator: (req) => req.headers['x-api-key'] || req.ip,
  message: 'Rate limit exceeded. Please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});