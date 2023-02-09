import React, { useMemo, useEffect, useState, useCallback } from "react";
import { App, mainComponents, wrapperComponents, addLangToPathName, removeLangFromPathName } from "logicore-react-pages";

import { GenericForm as TheGenericForm, submitButtonWidgets } from "logicore-forms";

import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';

import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useLocation,
  useHistory,
  useNavigate,
} from "react-router-dom";

import { useTranslation, Trans } from 'react-i18next';
import './i18n';


import './App.scss';


const GameSubmit = () => {
  return <button type="submit" className="btn btn-success"><Trans>Start the game</Trans></button>;
};

Object.assign(submitButtonWidgets, { GameSubmit });

const addLang = (url) => addLangToPathName(window.CURRENT_LANGUAGE, url);

const MainWrapper = ({ player_name, result, onChange }) => {
  const Component = mainComponents[result?.template];
  const loc = useLocation();
  const getUrl = (lang) => {
    const theUrl = loc.pathname + loc.search;
    return addLangToPathName(lang, removeLangFromPathName(window.CURRENT_LANGUAGE, theUrl));
  }
	const { t } = useTranslation();
  return (
    <div className="d-flex flex-column" style={{height: "calc(max(100vh, 700px))"}}>
      <Navbar bg="light" expand="lg">
        <div className="container-fluid">
          {<Navbar.Brand href="javascript:void(0)"><Trans>Millionaire Game</Trans></Navbar.Brand>}
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Link className="nav-link" to={addLang("/")}><Trans>All games</Trans></Link>
            </Nav>
            <Nav className="ml-auto">
              {result.player_name &&
                <li className="nav-item">
                  <a className="nav-link active" aria-current="page" href="#" onClick={e => e.preventDefault()}>
                    <Trans>Name</Trans>: {result.player_name}
                  </a>
                </li>
              }
              <NavDropdown title={<><i className="fas fa-language"></i>{" "}{ window.CURRENT_LANGUAGE_NAME }</>} id="basic-nav-dropdown" align="end">
                {window.LANGUAGES.map(([code, name]) => {
                  return <NavDropdown.Item key={code} href={getUrl(code)}>{name}</NavDropdown.Item>;
                })}
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


const HomeView = (props) => {
  return <div className="container my-3">
    <h3><Trans>All games</Trans></h3>
		<table className="table table-border mt-3">
      <thead>
        <tr>
          <th><Trans>Name</Trans></th>
          <th><Trans>Start date and time</Trans></th>
          <th><Trans>End date and time</Trans></th>
        </tr>
      </thead>
      <tbody>
        {props.items?.map(item => (<tr>
          <td><Link to={addLang(`/game/${item.uuid}/`)}>{item.name}</Link></td>
          <td>{item.start_datetime}</td>
          <td>{item.end_datetime}</td>
        </tr>))}
      </tbody>
		</table>
  </div>;
};


const Game = (props) => {
  return <div className="container my-3">
    <h3><Trans>The Game</Trans>: «<Trans>{props.name}</Trans>»</h3>
    <div className="my-3"><Trans>Will end on</Trans>: {props.end_datetime}</div>
    <div className="my-5">
      <h5 className="my-2"><Trans>Question</Trans> {props.index} / {props.total}</h5>
      <blockquote className="blockquote">{props.text}</blockquote>
      <div className="d-grid" style={{gridTemplateColumns: "1fr 1fr", gridGap: 20}}>
        {[1,2,3,4].map(i => (
          <button key={i} type="button" className="btn btn-xl btn-outline-dark" style={{textAlign: "left"}} onClick={_ => props.onChange({questionId: props.pk, answer: i})}>
            {props[`answer${i}`]}
          </button>
        ))}
      </div>
    </div>
  </div>;
};


const GameWillStart = (props) => {
  return <div className="container my-3">
    <h3><Trans>The Game</Trans></h3>
    <h2>«<Trans>{props.name}</Trans>»</h2>
    <div><Trans>Will start on:</Trans> {props.start_datetime}</div>
  </div>;
};


const GameEnded = (props) => {
  return <div className="container my-3">
    <h3><Trans>The Game</Trans></h3>
    <h2>«<Trans>{props.name}</Trans>»</h2>
    <div><Trans>Has ended on:</Trans> {props.end_datetime}</div>
  </div>;
};


const GameFinish = (props) => {
  return <div className="container my-3">
    <h3><Trans>Thank you for participating in a game</Trans></h3>
    <h2>«<Trans>{props.name}</Trans>»</h2>
    <div><Trans>Results will be published on</Trans>: {props.end_datetime}</div>
  </div>;
};

const PageNotFound = () => {
  return <div style={{position: "fixed", top: 60, left: 0, right: 0, bottom: 0, display: "flex", justifyContent: "center", alignItems: "center"}}>
    <div><Trans>Page not found</Trans>. <Link to={addLang("/")}><Trans>Visit Home</Trans></Link></div>
  </div>;
}

const GenericForm = (props) => {
  return <div className="container my-3">
    <h3>{props.title}</h3>
    <TheGenericForm {...props} />
  </div>;
}

Object.assign(mainComponents, {
  HomeView,
  PageNotFound,
  GenericForm,
  Game,
  GameFinish,
  GameWillStart,
  GameEnded,
});

export default App;
