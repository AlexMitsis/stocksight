import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChangePasswordForm } from '@/components/profile/ChangePasswordForm';
import { ChangeEmailForm } from '@/components/profile/ChangeEmailForm';
import { ChangeCurrencyForm } from '@/components/profile/ChangeCurrencyForm';
import { ChangeCountryForm } from '@/components/profile/ChangeCountryForm';

export const ProfilePage = () => {
  const { user } = useAuth();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showChangeEmail, setShowChangeEmail] = useState(false);
  const [showChangeCurrency, setShowChangeCurrency] = useState(false);
  const [showChangeCountry, setShowChangeCountry] = useState(false);

  if (!user) {
    return null;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Profile Settings</h1>

      <div className="grid gap-6 md:grid-cols-2">
        {/* User Information */}
        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
            <CardDescription>Your account details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-semibold text-muted-foreground">Email</p>
              <p className="text-lg">{user.email}</p>
            </div>

            <div>
              <p className="text-sm font-semibold text-muted-foreground">Country</p>
              <p className="text-lg">{user.country || 'Not set'}</p>
            </div>

            <div>
              <p className="text-sm font-semibold text-muted-foreground">Preferred Currency</p>
              <p className="text-lg">{user.preferred_currency}</p>
            </div>

            <div>
              <p className="text-sm font-semibold text-muted-foreground">Account Created</p>
              <p className="text-lg">
                {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </p>
            </div>

            <div>
              <p className="text-sm font-semibold text-muted-foreground">Account Status</p>
              <p className="text-lg">
                {user.is_active ? (
                  <span className="text-green-600 dark:text-green-400">Active</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">Inactive</span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>Manage your account settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Button
                onClick={() => {
                  setShowChangeCountry(!showChangeCountry);
                  setShowChangeCurrency(false);
                  setShowChangePassword(false);
                  setShowChangeEmail(false);
                }}
                variant="outline"
                className="w-full"
              >
                Change Country
              </Button>
            </div>

            <div>
              <Button
                onClick={() => {
                  setShowChangeCurrency(!showChangeCurrency);
                  setShowChangeCountry(false);
                  setShowChangePassword(false);
                  setShowChangeEmail(false);
                }}
                variant="outline"
                className="w-full"
              >
                Change Currency
              </Button>
            </div>

            <div>
              <Button
                onClick={() => {
                  setShowChangePassword(!showChangePassword);
                  setShowChangeCountry(false);
                  setShowChangeEmail(false);
                  setShowChangeCurrency(false);
                }}
                variant="outline"
                className="w-full"
              >
                Change Password
              </Button>
            </div>

            <div>
              <Button
                onClick={() => {
                  setShowChangeEmail(!showChangeEmail);
                  setShowChangeCountry(false);
                  setShowChangePassword(false);
                  setShowChangeCurrency(false);
                }}
                variant="outline"
                className="w-full"
              >
                Change Email
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Change Password Form */}
        {showChangePassword && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>Update your account password</CardDescription>
            </CardHeader>
            <CardContent>
              <ChangePasswordForm
                onSuccess={() => {
                  setShowChangePassword(false);
                }}
                onCancel={() => {
                  setShowChangePassword(false);
                }}
              />
            </CardContent>
          </Card>
        )}

        {/* Change Email Form */}
        {showChangeEmail && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Change Email</CardTitle>
              <CardDescription>Update your email address</CardDescription>
            </CardHeader>
            <CardContent>
              <ChangeEmailForm
                onSuccess={() => {
                  setShowChangeEmail(false);
                }}
                onCancel={() => {
                  setShowChangeEmail(false);
                }}
              />
            </CardContent>
          </Card>
        )}

        {/* Change Currency Form */}
        {showChangeCurrency && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Change Preferred Currency</CardTitle>
              <CardDescription>Update your default currency for stock prices and financial data</CardDescription>
            </CardHeader>
            <CardContent>
              <ChangeCurrencyForm
                onSuccess={() => {
                  setShowChangeCurrency(false);
                }}
                onCancel={() => {
                  setShowChangeCurrency(false);
                }}
              />
            </CardContent>
          </Card>
        )}

        {/* Change Country Form */}
        {showChangeCountry && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Change Country</CardTitle>
              <CardDescription>Update your country of residence</CardDescription>
            </CardHeader>
            <CardContent>
              <ChangeCountryForm
                onSuccess={() => {
                  setShowChangeCountry(false);
                }}
                onCancel={() => {
                  setShowChangeCountry(false);
                }}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};
