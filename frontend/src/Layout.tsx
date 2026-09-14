import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="atlas">
      <div className="atlas-dock">
        <NavLink to="/" className="atlas-brand" end>
          Skewgrid
        </NavLink>
        <nav>
          <NavLink to="/layers">图层</NavLink>
          <NavLink to="/scans">扫描</NavLink>
          <NavLink to="/jobs">任务</NavLink>
          <NavLink to="/settings">设置</NavLink>
        </nav>
      </div>
      <Outlet />
    </div>
  );
}
