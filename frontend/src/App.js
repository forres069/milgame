import React, { useMemo, useEffect, useState, useCallback } from "react";
import { App, mainComponents, wrapperComponents, addLangToPathName, removeLangFromPathName } from "logicore-react-pages";

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

const addLang = (url) => addLangToPathName(window.CURRENT_LANGUAGE, url);

const MainWrapper = ({ result, onChange }) => {
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
  </div>;
};

Object.assign(mainComponents, {
    HomeView,
});

console.log(addLangToPathName);

export default App;
