import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';

import Dashboard from './pages/Dashboard';
import News from './pages/News';
import Market from './pages/Market';
import Global from './pages/Global';
import Backtest from './pages/Backtest';
import Report from './pages/Report';
import Analysis from './pages/Analysis';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'news', element: <News /> },
      { path: 'market', element: <Market /> },
      { path: 'global', element: <Global /> },
      { path: 'backtest', element: <Backtest /> },
      { path: 'report', element: <Report /> },
      { path: 'analysis', element: <Analysis /> },
    ],
  },
]);
