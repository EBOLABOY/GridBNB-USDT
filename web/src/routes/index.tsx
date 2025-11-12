/**
 * 路由配置
 */

import { lazy } from 'react';
import type { RouteObject } from 'react-router-dom';
import AuthGuard from '@/components/AuthGuard';
import BasicLayout from '@/layouts/BasicLayout';

// 懒加载页面组件
const Login = lazy(() => import('@/pages/Login'));
const Home = lazy(() => import('@/pages/Home'));
const ConfigList = lazy(() => import('@/pages/Config/List'));
const ConfigDetail = lazy(() => import('@/pages/Config/Detail'));
const TemplateList = lazy(() => import('@/pages/Template/List'));
const GridConfig = lazy(() => import('@/pages/Template/GridConfig'));
const AIConfig = lazy(() => import('@/pages/Template/AIConfig'));
const UserProfile = lazy(() => import('@/pages/User/Profile'));
const Logs = lazy(() => import('@/pages/Logs'));
const Trades = lazy(() => import('@/pages/Trades'));

// 路由配置
const routes: RouteObject[] = [
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <BasicLayout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'configs',
        element: <ConfigList />,
      },
      {
        path: 'configs/:id',
        element: <ConfigDetail />,
      },
      {
        path: 'templates',
        element: <TemplateList />,
      },
      {
        path: 'templates/grid/:id',
        element: <GridConfig />,
      },
      {
        path: 'templates/ai/:id',
        element: <AIConfig />,
      },
      {
        path: 'logs',
        element: <Logs />,
      },
      {
        path: 'trades',
        element: <Trades />,
      },
      {
        path: 'profile',
        element: <UserProfile />,
      },
    ],
  },
];

export default routes;
