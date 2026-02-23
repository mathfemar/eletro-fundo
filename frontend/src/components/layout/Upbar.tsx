import { NavLink, useLocation } from 'react-router-dom';
import { sections } from '@/config/navigation';
import './Upbar.css';

export default function Upbar() {
    const location = useLocation();

    // Seções que aparecem na Upbar: todas exceto a home (basePath '/')
    const upbarSections = sections.filter(s => s.id !== 'home');

    return (
        <header className="upbar">
            <nav className="upbar-sections">
                {upbarSections.map(section => {
                    const isActive = location.pathname.startsWith(section.basePath);
                    return (
                        <NavLink
                            key={section.id}
                            to={section.basePath}
                            className={`upbar-section-link${isActive ? ' active' : ''}`}
                        >
                            {section.label}
                        </NavLink>
                    );
                })}
            </nav>
            <div className="upbar-right">
                <span className="upbar-breadcrumb">Fundinho</span>
            </div>
        </header>
    );
}
