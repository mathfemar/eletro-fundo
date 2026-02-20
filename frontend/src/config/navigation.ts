export interface NavItem {
    label: string;
    href: string;
    icon: string;          // classe Font Awesome
    children?: NavItem[];
}

export interface Section {
    id: string;
    label: string;
    basePath: string;
    navItems: NavItem[];
}

export const sections: Section[] = [
    {
        id: 'home',
        label: 'Início',
        basePath: '/',
        navItems: [
            {
                label: 'Página Inicial',
                href: '/',
                icon: 'fas fa-home',
            },
        ],
    },
];
