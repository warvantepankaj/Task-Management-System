import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, KeyRound, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';
import Input from '../components/common/Input';
import Button from '../components/common/Button';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await authAPI.forgotPassword({ email });
      // The backend always returns 202 — show the same confirmation regardless
      // of whether the email actually exists. This is intentional.
      setSent(true);
    } catch (error) {
      // Network / unexpected failures only — 202 doesn't throw.
      toast.error(
        error.response?.data?.detail || 'Something went wrong. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full"
      >
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
              {sent ? (
                <CheckCircle2 className="w-8 h-8 text-primary-600" />
              ) : (
                <KeyRound className="w-8 h-8 text-primary-600" />
              )}
            </div>
            <h2 className="text-3xl font-bold text-gray-900">
              {sent ? 'Check your email' : 'Forgot password?'}
            </h2>
            <p className="text-gray-600 mt-2">
              {sent
                ? "If an account exists for that email, we've sent a reset link."
                : "Enter your email and we'll send you a reset link."}
            </p>
          </div>

          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="Email"
                type="email"
                icon={<Mail size={20} />}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                loading={loading}
              >
                Send reset link
              </Button>
            </form>
          ) : (
            <p className="text-sm text-gray-600 text-center">
              The link expires in 60 minutes. Be sure to check your spam folder.
            </p>
          )}

          <p className="text-center text-sm text-gray-600 mt-6">
            Remembered it?{' '}
            <Link
              to="/login"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Back to sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default ForgotPassword;
