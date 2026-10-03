import React, { createContext, useContext } from 'react';

export interface ThemeContextValue {
  accentColor: string;
  glowColor: string;
}

const ThemeContext = createContext<ThemeContextValue>({
  accentColor: 'var(--accent-primary)',
  glowColor: 'rgba(255, 255, 255, 0.12)',
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ThemeContext.Provider
      value={{
        accentColor: 'var(--accent-primary)',
        glowColor: 'rgba(255, 255, 255, 0.12)',
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextValue => {
  return useContext(ThemeContext);
};
