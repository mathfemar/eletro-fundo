import './Home.css';

export default function Home() {
    return (
        <div className="home-page">
            <div className="home-hero">
                <h1 className="home-title">
                    Bem-vindo ao <span className="text-accent">Fundinho</span>
                </h1>
                <p className="home-subtitle">
                    Plataforma de análise de fundos de investimento com dados em tempo real.
                </p>
            </div>
        </div>
    );
}
