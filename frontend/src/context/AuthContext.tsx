import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

type Role = 'developer' | 'manager' | null;

interface AuthContextType {
  role: Role;
  login: () => void;
  logout: () => void;
  getToken: () => Promise<string | undefined>;
  isAuthenticated: boolean;
  isLoading: boolean;
  user?: any;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const {
    isAuthenticated,
    isLoading,
    user,
    loginWithRedirect,
    logout: auth0Logout,
    getAccessTokenSilently
  } = useAuth0();

  let role: Role = null;

  if (isAuthenticated && user) {
    // Decode role from custom claims
    const roles = user['https://stateful-agent.com/roles'] || user['https://ai.code.agent/roles'] || user['roles'] || user['http://schemas.microsoft.com/ws/2008/06/identity/claims/role'] || [];
    const userRoles = roles.map((r: string) => r.toLowerCase());


    if (userRoles.includes('admin') || userRoles.includes('manager')) {
      role = 'manager';
    } else {
      role = 'developer';
    }
  }

  const login = () => loginWithRedirect();
  const logout = () => auth0Logout({ logoutParams: { returnTo: window.location.origin } });

  const getToken = async () => {
    try {
      return await getAccessTokenSilently();
    } catch (e) {
      return undefined;
    }
  };

  return (
    <AuthContext.Provider value={{ role, login, logout, getToken, isAuthenticated, isLoading, user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
