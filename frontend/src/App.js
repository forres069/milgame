import React, { useState, useCallback } from "react";
import { App, mainComponents, wrapperComponents, addLangToPathName, removeLangFromPathName } from "logicore-react-pages";
import { GenericForm as TheGenericForm, submitButtonWidgets } from "logicore-forms";
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';
import { DateTime } from "luxon";
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Trans } from 'react-i18next';
import './i18n';
import './App.scss';

const GameSubmit = () => (
  <button type="submit" className="btn btn-success">
    <Trans>Start the game</Trans>
  </button>
);

const WelcomeSubmit = () => (
  <button type="submit" className="btn btn-success my-3">
    <Trans>Continue</Trans>
  </button>
);

Object.assign(submitButtonWidgets, { GameSubmit, WelcomeSubmit });

const addLang = (url) => addLangToPathName(window.CURRENT_LANGUAGE, url);

const MainWrapper = ({ user, result, onChange }) => {
  const Component = mainComponents[result?.template];
  const loc = useLocation();

  const getUrl = (lang) => {
    const theUrl = loc.pathname + loc.search;
    return addLangToPathName(lang, removeLangFromPathName(window.CURRENT_LANGUAGE, theUrl));
  };

  return (
    <div className="d-flex flex-column" style={{ height: "calc(max(100vh, 700px))" }}>
      <Navbar bg="light" expand="lg">
        <div className="container-fluid">
          <Navbar.Brand href="/">
            <Trans>Millionaire Game</Trans>
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Link className="nav-link" to={addLang("/")}>
                <Trans>All games</Trans>
              </Link>
            </Nav>
            <Nav className="ml-auto">
              {result.player_name && (
                <>
                  <li className="nav-item">
                    <span className="nav-link active">
                      <Trans>Name</Trans>: {result.player_name}
                    </span>
                  </li>
                  <li className="nav-item">
                    <Link className="nav-link text-success" to="/logout/">
                      <Trans>Logout</Trans>
                    </Link>
                  </li>
                </>
              )}
              <NavDropdown title={<><i className="fas fa-language"></i>{" "}{window.CURRENT_LANGUAGE_NAME}</>} id="basic-nav-dropdown" align="end">
                {window.LANGUAGES.map(([code, name]) => (
                  <NavDropdown.Item key={code} href={getUrl(code)}>
                    {name}
                  </NavDropdown.Item>
                ))}
              </NavDropdown>
            </Nav>
          </Navbar.Collapse>
        </div>
      </Navbar>
      {Component && result && <Component {...{ ...result, onChange }} />}
    </div>
  );
};

Object.assign(wrapperComponents, {
  MainWrapper,
});

const MediaComponent = ({ question }) => {
  const questionStyles = {
    width: '300px',
    height: 'auto',
    borderRadius: '15px',
    display: 'block',
    margin: '20px 0 20px 0',
  };
  const audioStyles = {
    margin: '20px 0 20px 0'
  }
  const videoStyles = {
    width: '600px',
    borderRadius: '15px',
    display: 'block',
    margin: '20px 0 20px 0',
  }
  
  switch (question.question_type) {
    case 'audio':
      return question.audio_file ? (
        <audio className="center" style={audioStyles} controls>
          <source src={question.audio_file} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
      ) : null;
    case 'video':
      return question.video_file ? (
        <video controls width="300" style={videoStyles}>
          <source src={question.video_file} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      ) : null;
    case 'photo':
      return question.photo_file ? (
        <img src={question.photo_file} alt="Question" style={questionStyles} />
      ) : null;
    default:
      return null;
  }
};



const HomeView = (props) => (
  <div className="container my-3">
    <h3><Trans>My games</Trans></h3>
    <table className="table table-border mt-3">
      <thead>
        <tr>
          <th><Trans>Name</Trans></th>
          <th><Trans>Position</Trans></th>
          <th><Trans>Last start</Trans></th>
        </tr>
      </thead>
      <tbody>
        {props.my_games?.map(item => (
          <tr key={item.pk}>
            <td><Link to={addLang(`/simple-game/${item.pk}/`)}>{item.name}</Link></td>
            <td>-</td>
            <td>{item.last_start ? DateTime.fromSQL(item.last_start).toLocaleString(DateTime.DATETIME_MED) : <Trans>Never</Trans>}</td>
          </tr>
        ))}
      </tbody>
    </table>
    <h3 className="mt-5"><Trans>All games</Trans></h3>
    <table className="table table-border mt-3">
      <thead>
        <tr>
          <th><Trans>Name</Trans></th>
        </tr>
      </thead>
      <tbody>
        {props.other_games?.map(item => (
          <tr key={item.pk}>
            <td><Link to={addLang(`/simple-game/${item.pk}/`)}>{item.name}</Link></td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const WelcomeView = (props) => (
  <div className="container my-3">
    <h3><Trans>Welcome! Please enter or create a name and a password</Trans></h3>
    <TheGenericForm {...props} />
  </div>
);

const Game = (props) => {
  const [selectedAnswer, setSelectedAnswer] = useState();
  const [correctAnswer, setCorrectAnswer] = useState();
  const [navigateTo, setNavigateTo] = useState();
  const navigate = useNavigate();

  const handleClick = useCallback((i) => {
    if (selectedAnswer) return;
    setSelectedAnswer(i);
    props.onChange({ questionId: props.pk, answer: i }, null, response => {
      if (response.correctAnswer) {
        setCorrectAnswer(response.correctAnswer);
      }
      setNavigateTo(response.navigate_url);
    });
  }, [props.pk, selectedAnswer, props.onChange]);

  return (
    <div className="container my-3">
      <h3><Trans>The Game</Trans>: «<Trans>{props.name}</Trans>»</h3>
      <div className="my-5">
        <h5 className="my-2"><Trans>Question</Trans> {props.index} / {props.total}</h5>
        <blockquote className="blockquote">{props.text}</blockquote>
        <MediaComponent question={props} />
        <div className="d-grid" style={{ gridTemplateColumns: "1fr 1fr", gridGap: 20 }}>
          {[1, 2, 3, 4].map(i => (
            <button
              key={i}
              type="button"
              className={`btn btn-xl btn-outline-dark ${selectedAnswer === i ? 'answer_selected' : ''} ${correctAnswer === i ? 'answer_correct' : ''}`}
              style={{ textAlign: "left" }}
              onClick={() => handleClick(i)}
              disabled={!!correctAnswer}
            >
              {props[`answer${i}`]}
            </button>
          ))}
          {!!navigateTo && (
            <button className="btn btn-xl btn-primary" onClick={() => navigate(navigateTo)}>
              <Trans>Next question</Trans>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const GameResults = (props) => (
  <div className="container my-3">
    <h3><Trans>The game</Trans></h3>
    <h2>«<Trans>{props.name}</Trans>»</h2>
    <div><Trans>Results</Trans></div>
    TODO
  </div>
);

const PageNotFound = () => (
  <div style={{ position: "fixed", top: 60, left: 0, right: 0, bottom: 0, display: "flex", justifyContent: "center", alignItems: "center" }}>
    <div>
      <Trans>Page not found</Trans>. <Link to={addLang("/")}>
        <Trans>Visit Home</Trans>
      </Link>
    </div>
  </div>
);

const GenericForm = (props) => (
  <div className="container my-3">
    <h3>{props.title}</h3>
    <TheGenericForm {...props} />
  </div>
);

Object.assign(mainComponents, {
  HomeView,
  WelcomeView,
  PageNotFound,
  GenericForm,
  Game,
  GameResults,
});

export default App;
